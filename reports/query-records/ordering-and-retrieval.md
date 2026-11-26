# Ordering, Retrieval & Pagination Analysis

## 1. Sorting Mechanics (`order_by`)

### UI Configuration & Serialization
In `QueryRecordsConfig.vue`, sorting criteria are authored as an array of row objects:
```javascript
order_by_rows = [
  { field: "status", direction: "asc" },
  { field: "creation", direction: "desc" }
]
```
During config synchronization (`sync_local_config`), this array is serialized into a single string:
`"status asc, creation desc"`.

### Backend Qualification: `_qualify_order_by()`
In `flexirule/ruleflow/core/action_handlers/query_records.py` (lines 1127–1148):

```python
def _qualify_order_by(self, reference_doctype: str, order_by: str | None) -> str | None:
    if not order_by or not reference_doctype:
        return order_by

    parts = [p.strip() for p in str(order_by).split(",") if p.strip()]
    qualified_parts = []
    for part in parts:
        tokens = part.split()
        field_token = tokens[0]
        direction = f" {tokens[1]}" if len(tokens) > 1 else ""

        if "`" in field_token or "(" in field_token:
            qualified_parts.append(f"{field_token}{direction}")
            continue

        dt, field = self._resolve_filter_doctype_and_field(reference_doctype, None, field_token)
        target_dt = dt or reference_doctype
        qualified_parts.append(f"`tab{target_dt}`.`{field}`{direction}")

    return ", ".join(qualified_parts)
```

#### Evaluation of `_qualify_order_by`
- **Purpose**: Fully qualifies column names with table aliases (e.g. `` `tabSales Order`.`status` asc ``) before passing them to Frappe.
- **Benefit**: Prevents `Ambiguous column name` SQL errors when filters or fields cause `DatabaseQuery` to generate `LEFT JOIN` clauses against child tables or linked DocTypes.
- **Delegation**: The qualified string is passed directly as `order_by` to `frappe.get_list()`, which places it into MariaDB's `ORDER BY` clause. Python-side sorting is **not** performed.

---

## 2. Retrieval Settings & Pagination

### Limit Computation (`limit_type` & `limit`)
In `_query_list()` (lines 1153–1167):

```python
limit_type = config.get("limit_type", "Custom Limit")
if limit_type == "All":
    limit = 0
elif limit_type == "First Record":
    limit = 1
else:
    limit_val = config.get("limit")
    if limit_val in (None, ""):
        limit = 20
    else:
        try:
            limit = int(limit_val)
        except ValueError:
            limit = 20
```

`limit` is passed as `limit_page_length` to `frappe.get_list()`:
- `limit_type: "All"` -> `limit_page_length = 0` -> SQL omits `LIMIT`.
- `limit_type: "First Record"` -> `limit_page_length = 1` -> SQL `LIMIT 1`.
- `limit_type: "Custom Limit"` -> `limit_page_length = N` -> SQL `LIMIT N`.

### Database-Level Execution Confirmation
All limits are applied at the database level by MariaDB/Postgres. Records are not loaded into Python and sliced afterward.

### Critical Pagination Gap: Missing Offset (`limit_start`)
Frappe's native `DatabaseQuery` supports `limit_start` (SQL `OFFSET`).
However, FlexiRule's `QueryRecordsConfig.vue` and `_query_list()` handler do **not** support or expose `limit_start` or `offset`.
Consequently, FlexiRule rules cannot paginate through large datasets in chunks (e.g., records 101–200).

---

## 3. Deduplication (`distinct`) and Grouping (`group_by`)

### Deduplication (`distinct`)
When `config.distinct` is truthy, `_query_list` passes `distinct=True` to `frappe.get_list()`.
`DatabaseQuery` prepends `DISTINCT` to the generated SQL `SELECT` statement:
`SELECT DISTINCT `tabSales Order`.`name` FROM ...`

### Grouping (`group_by`)
When `config.group_by` is specified in `Query List`, `_query_list` passes `group_by=config["group_by"]` to `frappe.get_list()`.
Additionally, dedicated `Group By` mode (`_group_by()`) constructs explicit SQL aggregation functions:
`fields=[group_expr, f"{safe_agg_fn}({agg_expr}) as value"], group_by=group_expr`.
All grouping and deduplication operations are executed natively within the database engine.
