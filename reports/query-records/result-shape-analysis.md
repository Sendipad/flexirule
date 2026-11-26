# Result Shape & Object Type Analysis: Query Records

## 1. Executive Findings on Returned Object Types

| Query Operation | Configured `return_type` | Runtime Python Data Class | Document Methods Accessible? | Contains Child Tables? |
| :--- | :--- | :--- | :---: | :---: |
| **Query List** | `List of Records` | `list[frappe.types.frappedict._dict]` | NO | NO (Unless joined) |
| **Query Doc** | `Single Record` | `frappe.types.frappedict._dict` | NO | YES |
| **Query Doc** | `Full Document` | `frappe.types.frappedict._dict` | NO | YES |
| **Exist Record** | `Yes / No` | `bool` | N/A | N/A |
| **Query Report** | `List of Records` | `dict{"columns": [...], "result": [...]}` | NO | NO |
| **Count** | `List of Values` | `int` | N/A | N/A |
| **Sum / Avg / Min / Max** | `List of Values` | `int` / `float` | N/A | N/A |
| **Group By** | `List of Records` | `list[frappe.types.frappedict._dict]` | N/A | N/A |

---

## 2. CRITICAL AUDIT QUESTION: Does Query Records Return Complete Documents?

### The Architectural Distinction

1. **Query Record (`frappe._dict`)**:
   A dictionary representation of SQL table columns returned by `frappe.get_list()` or `doc.as_dict()`.
   ```python
   # Query Record row:
   {"name": "SO-0001", "customer": "Acme Corp", "grand_total": 500.0}
   ```
   *Properties*: Light weight, JSON-serializable, contains no document methods (`doc.save()`, `doc.submit()`, `doc.get_formatted()`).

2. **Frappe Document Object (`frappe.model.document.Document`)**:
   An instantiated, active Frappe document controller instance returned by `frappe.get_doc()`.
   ```python
   doc = frappe.get_doc("Sales Order", "SO-0001")
   ```
   *Properties*: Rich active object with state tracking (`_doc_before_save`), ORM methods (`save()`, `db_set()`, `run_method()`), child table document controllers, and meta attachment.

---

## 3. Source Evidence from `_query_doc()`

In `flexirule/ruleflow/core/action_handlers/query_records.py` (lines 1115–1124):

```python
fetch_fn = frappe.get_cached_doc if strategy == "Get Doc from Cache" else frappe.get_doc

try:
    doc = fetch_fn(resolved_doctype, docname)
except frappe.DoesNotExistError:
    return None

if not ignore_permissions:
    doc.check_permission("read")

return doc.as_dict()
```

### Critical Findings

1. **`doc.as_dict()` Unconditionally Converts Objects**:
   Even though `Query Doc` fetches the full document controller using `frappe.get_doc()` or `frappe.get_cached_doc()`, it immediately converts it to a dictionary via `doc.as_dict()` before returning it to the engine.
2. **"Full Document" Option is Misleading**:
   In `QueryRecordsConfig.vue` and `get_operation_contracts()`, the user can select `return_type: "Full Document"`.
   However, the return value is **NOT** a `Document` instance; it is a dictionary containing all parent fields and child table rows as list of dicts.
3. **No Active Controller Persistence**:
   Subsequent rule engine nodes cannot invoke document methods (e.g. `doc.submit()`) directly on the context variable created by `Query Doc`. Downstream actions must use `Document Action` (which invokes `frappe.get_doc()` independently).

---

## 4. Result Shape by Operation

### `Query List` Output Shape
Returns a list of `frappe._dict` objects projected according to the `fields` array:
```json
[
  {"name": "SO-0001", "customer": "Acme Corp", "grand_total": 1500.0},
  {"name": "SO-0002", "customer": "Beta LLC", "grand_total": 850.0}
]
```

### `Query Doc` Output Shape
Returns a nested dictionary containing all document fields and child table arrays:
```json
{
  "name": "SO-0001",
  "doctype": "Sales Order",
  "customer": "Acme Corp",
  "docstatus": 1,
  "items": [
    {"name": "so-item-01", "item_code": "ITEM-A", "qty": 10, "rate": 150.0}
  ]
}
```

### `Query Report` Output Shape
Returns a dictionary containing serialized column definitions and row dicts:
```json
{
  "columns": [
    {"label": "Customer", "fieldname": "customer", "fieldtype": "Link"},
    {"label": "Total Amount", "fieldname": "total_amount", "fieldtype": "Currency"}
  ],
  "result": [
    {"customer": "Acme Corp", "total_amount": 1500.0}
  ]
}
```
