# Condition System

FlexiRule features a robust condition system that allows for visual construction of complex logic while maintaining high execution performance.

## Architecture

The system operates in two phases:

### 1. Design-time (Visual AST)
In the Rule Builder, conditions are constructed visually. This structure is saved as a JSON Abstract Syntax Tree (AST) in the `condition_json` field.
- **Groups**: Support `AND` / `OR` logic.
- **Conditions**: Compare fields (`left`) against values or other fields (`right`) using operators.
- **Collections**: Support `ANY` / `ALL` logic over child tables or lists (e.g., "Any item in Sales Invoice has qty > 10").

### 2. Runtime (Compiled Python)
When a Rule is saved, the `ConditionCompiler` translates the JSON AST into an optimized Python expression string, stored in `compiled_expression`.

**Example Conversion:**
- **Visual**: `(Status == "Open") AND (Grand Total > 1000)`
- **Compiled**: `(doc.get('status') == "Open" and doc.get('grand_total') > 1000)`

---

## Condition Compiler (`flexirule.ruleflow.core.compiler`)

The compiler ensures that conditions are valid Python and optimized for the `frappe.safe_eval` environment.

### Supported Operators
- **Comparison**: `==`, `!=`, `>`, `<`, `>=`, `<=`
- **Membership**: `in`, `not in`
- **Identity**: `is`, `is not` (for `None` checks)
- **String**: `contains`, `not_contains`
- **Existence**: `is_set`, `is_not_set` (checks for `None` or empty string)
- **Collection**: `is_empty`, `is_not_empty`, `length_eq`, `length_gt`, etc.
- **Frappe Specific**: `is_submittable`, `has_field`

### Scope Resolution
The compiler automatically prefixes field names with the correct scope:
- `doc.fieldname`: Accesses the current document state.
- `old_doc.fieldname`: Accesses the document state before the current change (useful for "On Change" logic).
- `vars.varname`: Accesses variables in the execution context.
- `row.fieldname`: Accesses fields in a collection during an `ANY`/`ALL` check.

For deep paths (e.g., `doc.items.0.item_code`), the compiler uses a `resolve()` helper to safely traverse nested objects.

---

## Evaluation Environment

Conditions are evaluated in a sandboxed environment using `frappe.safe_eval`.

### Available Globals
- `doc`: Current document.
- `old_doc`: Document before save.
- `vars`: Execution variables.
- `frappe`: The `SafeFrappeAPI` (read-only methods only).
- `rule`: Metadata about the current rule.
- `caller`: Metadata about the calling rule (if a sub-rule).
- **Utilities**: `resolve`, `check_link_match`, `length_of`, `is_empty_value`.

### Performance Optimizations
- **Pre-compilation**: The engine evaluates the Python string directly, avoiding JSON parsing at runtime.
- **Watched Fields**: The compiler extracts field dependencies from the condition. The `RuleCoordinator` uses this to skip rules if none of the "watched" fields have changed.
- **Caching**: Compiled expressions are cached in the `Runtime Registry` (Redis) for immediate access.

---

## Security

- **SafeFrappeAPI**: Prevents conditions from performing database writes (e.g., `frappe.db.set_value`).
- **Syntax Validation**: The compiler validates the generated Python AST before saving to prevent syntax errors or malicious code injection.
- **Permission Checks**: Conditions can use `frappe.get_roles()` or `frappe.session.user` to implement role-based logic securely.
