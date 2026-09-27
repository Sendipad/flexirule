# Frappe Query & List API Source Analysis

## 1. Overview & Installed Frappe Target

- **Frappe Version**: `15.121.1`
- **Source Location**: `/home/jules/frappe-bench/apps/frappe`
- **Core Query Files**:
  - `frappe/__init__.py` (Top-level API facade)
  - `frappe/database/database.py` (Database interface wrapper)
  - `frappe/model/db_query.py` (`DatabaseQuery` query engine)

---

## 2. API Call Chains in Frappe v15

Frappe provides two primary entry points for list-based record retrieval: `frappe.get_list()` and `frappe.get_all()`.

```
frappe.get_list(doctype, **kwargs)
      ↓
frappe.model.db_query.DatabaseQuery(doctype).execute(*args, **kwargs)
      ↓
DatabaseQuery.build_and_run()
      ↓
frappe.db.sql(query, as_dict=True)
```

### Distinction Between `frappe.get_list` and `frappe.get_all`

In `frappe/__init__.py` (lines 2020–2058):

```python
def get_list(doctype, *args, **kwargs):
    import frappe.model.db_query
    return frappe.model.db_query.DatabaseQuery(doctype).execute(*args, **kwargs)

def get_all(doctype, *args, **kwargs):
    kwargs["ignore_permissions"] = True
    if "limit_page_length" not in kwargs:
        kwargs["limit_page_length"] = 0
    return get_list(doctype, *args, **kwargs)
```

#### Key Differences
1. **Permissions**: `get_list()` enforces user read permissions, User Permissions, and Permission Query Conditions by default (`ignore_permissions=False`). `get_all()` sets `ignore_permissions=True`.
2. **Default Pagination Limit**:
   - `get_list()` defaults `limit_page_length` to `20` (set inside `DatabaseQuery.execute`).
   - `get_all()` defaults `limit_page_length` to `0` (unlimited, returning all matching records).

---

## 3. Deep Architectural Inspection of `DatabaseQuery`

The entire query generation pipeline lives in `frappe/model/db_query.py`.

### Execution Flow inside `DatabaseQuery.execute()`

1. **Permission Guard** (lines 351–352):
   ```python
   if not ignore_permissions:
       self.check_read_permission(self.doctype, parent_doctype=parent_doctype)
   ```
2. **Field Resolution** (lines 364–367):
   If `fields` is not provided, defaults to ``[`tab{doctype}`.`{pluck or 'name'}`]``.
3. **Limit Handling** (lines 369–373, 381):
   - `limit_start` maps to SQL `OFFSET`.
   - `limit_page_length` maps to SQL `LIMIT`.
4. **Query Building & Sanitation**:
   - `self.prepare_args()`: Validates tables, parses virtual DocTypes, cleans fields.
   - `self.sanitize_fields()`: Prevents unauthorized SQL functions or subqueries.
   - `self.build_conditions()`: Parses dict and list filters, converts operators (`in`, `not in`, `like`, `between`, `is`), builds permission match conditions, and handles child table joins.
5. **SQL Execution**:
   Executes `frappe.db.sql()` with `as_dict=True` (or `as_dict=False` / list depending on `as_list` or `pluck`).

---

## 4. Comprehensive Frappe Query Engine Capabilities Inventory

| Query Feature | Native Frappe Parameter | Native Frappe Syntax / Behavior |
| :--- | :--- | :--- |
| **Field Selection** | `fields` | `["name", "creation"]`, `["*"]`, `["count(name) as count"]`. `*` expands to all table columns. |
| **Pluck Single Field** | `pluck` | `pluck="email"` returns a flat list of strings `['a@x.com', 'b@x.com']` instead of dicts. |
| **Dict Filters** | `filters` | `{"status": "Open", "company": "Acme"}` -> `status='Open' AND company='Acme'`. |
| **List Filters** | `filters` | `[["status", "=", "Open"], ["grand_total", ">", 1000]]`. |
| **Child Table Filters** | `filters` | `[["Sales Order Item", "item_code", "=", "ITEM-001"]]` triggers auto-`LEFT JOIN`. |
| **Comparison Operators** | `filters` | `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `not like`, `in`, `not in`, `between`, `is`, `is not`. |
| **Or Filters** | `or_filters` | `[["status", "=", "Open"], ["status", "=", "Pending"]]` rendered as `(cond1 OR cond2)`. |
| **Ordering** | `order_by` | `"creation desc, status asc"`. Sanitized by `validate_order_by_and_group_by()`. |
| **Pagination Length** | `limit_page_length` / `limit` | Integer value for SQL `LIMIT`. `0` or `None` removes limit. |
| **Pagination Offset** | `limit_start` / `start` | Integer value for SQL `OFFSET`. Default `0`. |
| **Deduplication** | `distinct` | `distinct=True` prepends `DISTINCT` to `SELECT`. |
| **Grouping** | `group_by` | `"status"` or `"customer"` generates SQL `GROUP BY`. |
| **Permissions** | `ignore_permissions` | `False` applies `build_match_conditions()` and `apply_fieldlevel_read_permissions()`. |

---

## 5. Summary Findings for Architectural Alignment

Frappe's `frappe.get_list()` provides a complete, secure, and performant Python abstraction over MariaDB / Postgres query generation. Any upper-level framework (such as FlexiRule) should construct clean parameters (`fields`, `filters`, `or_filters`, `order_by`, `limit_page_length`, `limit_start`, `distinct`, `group_by`) and pass them directly to `frappe.get_list()`.
