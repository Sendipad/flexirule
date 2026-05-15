# Condition System Technical Details

FlexiRule's condition system balances visual simplicity with Python's expressive power.

## Compiled Expression Logic

When a Rule is saved, the `ConditionCompiler` translates the visual JSON structure into a string.

### Regex-Based Field Extraction
To optimize performance, the `RuleCoordinator` must know which fields a condition depends on *without* actually evaluating the Python string. This is done using regex patterns during compilation to extract **Watched Fields**:

```python
COMPILED_FIELD_PATTERNS = (
    re.compile(r"\b(?:doc|old_doc)\.([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"\b(?:doc|old_doc)\.get\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"\bresolve\(\s*(?:doc|old_doc)\s*,\s*['\"]([^'\"]+)['\"]"),
)
```
- **Pruning**: If `doc.status` is extracted, the coordinator will only run the rule if `status` is in the document's changed fields.

---

## Evaluation Environment: SafeFrappeAPI

To ensure that conditions cannot cause unintended side effects, they are executed via `frappe.safe_eval` with a restricted `frappe` global object called `SafeFrappeAPI`.

### Whitelisted (Read-Only) Methods
- `get_value`, `get_all`, `db_exists`, `get_meta`, `format_value`.
- `utils`: Access to `frappe.utils` (date math, etc.).

### Prohibited (Write) Methods
Any attempt to call the following will raise a `PermissionError`:
- `get_doc`, `new_doc`, `delete_doc`.
- `db_set_value`, `db.sql`, `db.commit`, `db.rollback`.

---

## Logical Grouping & Visual UI

### Hierarchical Logical Grouping (AND/OR)
- **Infinite Nesting**: Supports arbitrary depth of `AND` and `OR` groups.
- **Short-Circuiting**: Compiled Python strings leverage native `and`/`or` short-circuiting for performance.

### Visual Drag-and-Group UI
- **Active Reactivity**: Moving a condition in the UI immediately re-calculates the logic tree's structure.
- **Auto-Nesting**: Logic is scaffolded automatically when elements are dropped onto each other, ensuring a valid JSON AST is always maintained.

---

## Scope Resolution
- `doc.fieldname`: `doc.get('fieldname')`
- `old_doc.fieldname`: `old_doc.get('fieldname')`
- `vars.varname`: `vars.get('varname')`
- Deep Paths: `resolve(doc, 'items.0.qty')`
