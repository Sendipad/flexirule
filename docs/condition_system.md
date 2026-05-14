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

## Hierarchical Logical Grouping (AND/OR)

The condition system supports unlimited logical complexity through **Nested Hierarchical Grouping**.

- **Infinite Nesting**: You can create groups within groups (e.g., `(Group A AND Group B) OR (Group C AND Group D)`).
- **Logical Precision**: This allows for precise control over Boolean precedence, ensuring that complex business rules—such as those found in large-scale ERP systems—can be modeled accurately without code.

---

## Visual Drag-and-Group UI

Managing complex logic trees is made intuitive through the builder's specialized drag-and-drop interface:

- **Dynamic Regrouping**: Users can drag an existing condition or an entire group into another group to instantly change the logical structure.
- **Auto-Nesting**: Dragging one condition directly onto another automatically scaffolds a new `AND` group, facilitating rapid logic building.
- **Visual Clarity**: The UI uses indented, color-coded blocks to represent hierarchical levels, making it easy to audit even the most complex logic at a glance.

This fluid interface ensures that as your business requirements change, your logic can be rearranged and expanded with zero technical overhead.

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
