# Executive Summary: FlexiRule "Query Records" Audit

## Executive Summary Table

| Question | Finding | Evidence |
| :--- | :--- | :--- |
| **Uses native Frappe query API?** | **YES** (Hybrid Delegation) | `Query List`, `Exist Record`, `Count`, `Sum`, `Average`, `Min`, `Max`, `Group By` call `frappe.get_list()`. `Query Doc` uses `frappe.get_doc()` / `frappe.get_cached_doc()` / `frappe.get_all()`. `Query Report` calls `frappe.desk.query_report.run()`. |
| **Selected fields supported?** | **YES** | Configured `fields` array is passed directly to `frappe.get_list(fields=fields)`. Database-level column projection. |
| **Full query list supported?** | **YES** | `Query List` mode retrieves rows as a list of `frappe._dict` objects. `limit_type: "All"` passes `limit_page_length=0` to fetch all rows. |
| **Full Document objects supported?** | **NO** (Returned as dicts) | Even when `return_type` is configured as `"Full Document"`, `_query_doc` invokes `doc.as_dict()` before returning, producing a `frappe._dict` dictionary, not an active `frappe.model.document.Document` instance. |
| **`order_by` respected?** | **YES** | Frontend converts sort rows to `"field asc/desc"` strings; backend qualifies table names via `_qualify_order_by()` and passes string to `frappe.get_list(order_by=...)`. |
| **Retrieval settings respected?** | **PARTIALLY** | `limit_type` ("All", "First Record", "Custom Limit") and `limit` are respected. Pagination offset (`limit_start` / `offset`) is **NOT** exposed or supported. |
| **Pagination database-level?** | **YES** (For length) | `limit_page_length` is passed to `frappe.get_list()` and executed via SQL `LIMIT`. Offset/start is absent. |
| **Custom query engine?** | **NO** | FlexiRule does not maintain a custom query parser or direct SQL builder for standard queries; it acts as a configuration and normalization layer over Frappe APIs. |
| **Custom filtering?** | **PARTIALLY** (Normalization layer) | Filter conditions are resolved and normalized in Python (`_resolve_query_filters`), then passed as standard Frappe filter lists to `frappe.get_list()`. |
| **Custom ordering?** | **NO** | Ordering is delegated directly to Frappe/MariaDB SQL `ORDER BY`. FlexiRule only qualifies table aliases (`_qualify_order_by`). |
| **Permission behavior** | **SECURE** | Uses `frappe.get_list()` by default (respecting DocType permissions). Bypassing permissions requires `ignore_permissions: 1`, System Manager role (or hook allowlist), and an explicit `permission_audit_reason`. |
| **Major contract gaps** | **IDENTIFIED** | 1. `return_type="Full Document"` returns `dict`, not `Document`.<br>2. Missing pagination offset (`limit_start`).<br>3. `Query Doc` operation schema mismatch between backend contract (`action_overrides`) and UI implementation. |

---

## Definitive Answers to the 18 Key Questions

### Q1: Does Query Records respect every configuration field currently exposed by the UI?
**Answer: PARTIALLY**
- **Respected Fields**: `filters`, `fields`, `order_by`, `limit_type`, `limit`, `group_by`, `distinct`, `parent_doctype`, `fetch_strategy`, `doctype_name`, `docname`, `ignore_permissions`, `permission_audit_reason`.
- **Ignored / Mismatched Fields**:
  1. `return_type`: Configurable as `"Single Record"` or `"Full Document"` in `Query Doc`, but backend `_query_doc` unconditionally executes `doc.as_dict()`, ignoring the distinction.
  2. `reference_docname`: Mandatory in `Query Report` backend validation contract, but in `Query Report` mode the UI stores report name in `reference_docname` while backend reads `config.report_name`.

### Q2: Can it retrieve the entire query result list?
**Answer: YES**
- In `Query List` mode, setting `limit_type: "All"` causes `_query_list` to set `limit = 0`, which passes `limit_page_length=0` to `frappe.get_list()`. Frappe's `DatabaseQuery` interprets `limit_page_length=0` as omitting the SQL `LIMIT` clause, returning all matching records.

### Q3: Can it retrieve only explicitly selected fields?
**Answer: YES**
- `config.fields` (e.g., `["name", "status", "customer"]`) is passed directly to `frappe.get_list(fields=fields)`. `DatabaseQuery` projects only these columns in the SQL `SELECT` statement.

### Q4: Can it retrieve all fields using `"*"`, if supported?
**Answer: YES**
- Supplying `fields: ["*"]` passes `["*"]` to `frappe.get_list()`. `DatabaseQuery.prepare_args()` expands `*` into all standard standard columns of the target DocType table.

### Q5: Does it respect `order_by`?
**Answer: YES**
- The UI allows multi-column sort configuration (`order_by_rows`). These are serialized into a comma-separated string (e.g. `"status asc, creation desc"`). Backend `_qualify_order_by()` qualifies field references (e.g., `` `tabSales Order`.`status` asc ``) to prevent SQL join ambiguity, then passes it directly to `frappe.get_list(order_by=...)`.

### Q6: Does it respect limit/pagination/retrieval settings?
**Answer: PARTIALLY**
- **Limit Length**: Respected (`limit_type` "All" -> `0`, "First Record" -> `1`, "Custom Limit" -> user input or default `20`).
- **Pagination Offset**: **Not Supported**. There is no `limit_start` or `offset` field in the UI or backend `_query_list` handler. Paging beyond page 1 is impossible.

### Q7: Are those settings applied at the database query level or after retrieval?
**Answer: DATABASE LEVEL**
- Limits are passed directly as `limit_page_length` to `frappe.get_list()`, which appends `LIMIT <n>` to the SQL query. Slicing is not performed in Python.

### Q8: Does it return query-result dictionaries or actual Frappe `Document` objects?
**Answer: QUERY-RESULT DICTIONARIES (`frappe._dict`)**
- `Query List` returns a `list` of `frappe._dict` objects.
- `Query Doc` loads the document via `frappe.get_doc()` or `frappe.get_cached_doc()`, but explicitly calls `.as_dict()` before returning. It **never** returns an active `frappe.model.document.Document` instance.

### Q9: Does it use Frappe's standard query/list APIs?
**Answer: YES**
- Standard modes (`Query List`, `Count`, `Sum`, `Average`, `Min`, `Max`, `Group By`, `Exist Record`) invoke `frappe.get_list()`. `Query Doc` invokes `frappe.get_doc()` or `frappe.get_all()`. `Query Report` invokes `frappe.desk.query_report.run()`.

### Q10: Does it use Query Builder?
**Answer: NO**
- FlexiRule does not construct PyPika / `frappe.qb` query objects for Query Records. (Note: Helper method `_apply_qb_filters` exists on `QueryRecordsHandler`, but primary execution delegates to `frappe.get_list`).

### Q11: Does it use direct SQL?
**Answer: NO**
- `frappe.db.sql()` is not directly called by FlexiRule for standard record queries. (`Query Report` invokes `frappe.desk.query_report.run()`, which internally uses direct SQL for script/query reports).

### Q12: Does it implement custom filtering, ordering, pagination, or field selection?
**Answer: NO (Delegates to Frappe)**
- FlexiRule normalizes and resolves expressions in filter values (e.g. `{doc.customer}` -> `"CUST-001"`), but delegates filter condition rendering, ordering, pagination, and field selection to Frappe's `DatabaseQuery`.

### Q13: Does it correctly respect Frappe permissions?
**Answer: YES**
- By using `frappe.get_list()` (rather than `frappe.get_all()` or `frappe.db.sql()`), standard user role permissions, User Permissions, and Permission Query Conditions are strictly enforced by Frappe.

### Q14: Does it expose or support `ignore_permissions`?
**Answer: YES (With Strict Security Enforcement)**
- Exposes `ignore_permissions` ("Skip Permissions") in UI. Bypassing permissions requires the executing user to possess the `System Manager` role (or role in `flexirule_ignore_permissions_roles` hook) AND supply a mandatory `permission_audit_reason`. Bypasses are logged to `flexirule.security`.

### Q15: Are there configuration fields that exist in the UI but are ignored by the backend?
**Answer: YES**
- `return_type` in `Query Doc` mode (UI exposes "Single Record" vs "Full Document", but backend ignores this choice and always returns `doc.as_dict()`).

### Q16: Are there backend capabilities that cannot be configured through the UI?
**Answer: YES**
- `or_filters` is supported in backend `_query_list` kwargs and filter normalization, but the Vue UI (`QueryRecordsConfig.vue` / `FilterGroup.vue`) only provides controls for AND filters.
- `limit_start` (SQL `OFFSET`) is supported by Frappe `DatabaseQuery`, but not exposed in FlexiRule UI or backend handler kwargs.

### Q17: Are there semantic differences between native Frappe querying and FlexiRule Query Records?
**Answer: MINOR**
- 1. In `Query Report` mode, `ignore_permissions` is ineffective because `frappe.desk.query_report.run()` internally enforces report read permissions independently.
- 2. Field qualification in `_qualify_order_by` automatically prefixes `` `tabDocType`. `` to prevent SQL join ambiguities on child tables, which is safer than raw Frappe string passing.

### Q18: Are there performance or security implications from those differences?
**Answer: YES**
- **Performance**: Fetching `return_type="Full Document"` via `frappe.get_doc()` loads all child tables, document attachments, and triggers document setup hooks in memory before calling `.as_dict()`, creating CPU and memory overhead when only scalar fields are needed.
- **Security**: Security model is robust. Permission bypasses are gated behind role checks, mandatory audit reasons, and security warning log entries. Filter validation (`_validate_doctype_field_references`) prevents field injection.
