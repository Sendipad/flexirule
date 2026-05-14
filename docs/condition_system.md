# Condition System

FlexiRule features a robust condition system that allows for visual construction of complex logic while maintaining high execution performance.

## Architecture

The system operates in two phases:

### 1. Design-time (Visual AST)
In the Rule Builder, conditions are constructed visually. This structure is saved as a JSON Abstract Syntax Tree (AST) in the `condition_json` field.
- **Groups**: Support `AND` / `OR` logic.
- **Conditions**: Compare fields (`left`) against values or other fields (`right`) using operators.
- **Collections**: Support `ANY` / `ALL` logic over child tables or lists.

### 2. Runtime (Compiled Python)
When a Rule is saved, the `ConditionCompiler` translates the JSON AST into an optimized Python expression string.

---

## Logical Grouping & Visual Management

The FlexiRule condition builder is designed for unlimited complexity through hierarchical nesting and intuitive UI interactions.

### Hierarchical Logical Groups
Users can create deeply nested logic by combining `AND` and `OR` groups.
- **AND Groups**: All child conditions/groups must evaluate to `True`.
- **OR Groups**: At least one child condition/group must evaluate to `True`.
- **Nesting**: Groups can contain other groups, allowing for complex expressions like `(A AND B) OR (C AND (D OR E))`.

### Drag-and-Group UI
The builder provides a fluid, drag-and-drop interface for managing these logic trees:
- **Dynamic Reordering**: Move conditions between groups to change their logical precedence instantly.
- **Visual Grouping**: Drag one condition onto another to automatically create a new logical group.
- **Context-Switching**: Easily toggle a group's operator between `AND` and `OR` with a single click.

This system adapts to any business need, whether it's a simple ERP validation or a complex multi-layered orchestration flow, by making the underlying Boolean algebra visible and manipulatable without writing code.

---

## Condition Compiler (`flexirule.ruleflow.core.compiler`)

The compiler ensures that conditions are valid Python and optimized for the `frappe.safe_eval` environment.

### Supported Operators
- **Comparison**: `==`, `!=`, `>`, `<`, `>=`, `<=`
- **Membership**: `in`, `not in`
- **Identity**: `is`, `is not`
- **String**: `contains`, `not_contains`
- **Existence**: `is_set`, `is_not_set`
- **Collection**: `is_empty`, `is_not_empty`, `length_eq`, `length_gt`, etc.

### Scope Resolution
The compiler automatically prefixes field names with the correct scope:
- `doc.fieldname`: Current document state.
- `old_doc.fieldname`: State before save.
- `vars.varname`: Execution variables.
- `row.fieldname`: Items in a collection (child tables).

---

## Evaluation Environment

Conditions are evaluated in a sandboxed environment using `frappe.safe_eval`.

### Available Globals
- `doc`, `old_doc`, `vars`, `frappe` (SafeFrappeAPI), `rule`, `caller`.
- **Utilities**: `resolve`, `check_link_match`, `length_of`, `is_empty_value`.

### Performance & Security
- **Watched Fields**: The coordinator skips rules if none of the fields referenced in the condition have changed.
- **SafeFrappeAPI**: Blocks all database writes during condition evaluation.
- **Pre-compilation**: Eliminates the overhead of JSON parsing during the execution phase.
