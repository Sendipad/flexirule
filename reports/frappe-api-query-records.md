# Deep Architecture Investigation: Frappe Query API vs. FlexiRule Query Records

## 1. Executive Summary

This architectural report presents a deep, source-code-backed investigation comparing how the **Frappe Framework (v15+)** implements document querying versus the current implementation in **FlexiRule's Query Records** action handler.

Our findings show that while Frappe provides a highly optimized, old-school format-interpolated SQL generation layer (`DatabaseQuery`) equipped with robust AST/token-based query sanitization, its behavior when handling Child DocTypes and fine-grained permissions features is subtle and easily misunderstood.

When comparing this against **FlexiRule's Query Records** handler, we discovered:
1. **Critical Permission Bypass**: FlexiRule uses `frappe.get_all` for aggregate operations (`Count`, `Sum`, `Average`, etc.), which programmatically overrides `ignore_permissions` to `True`. This completely bypasses Frappe's native sharing, owner, and row-level user permissions.
2. **Child DocType Permission Failure**: Running list queries on child DocTypes directly with permissions enabled fails because FlexiRule does not forward `parent_doctype` to `get_list`.
3. **No Support for DISTINCT/Deduplication**: When left-joins on child table fields cause duplicate parent rows, FlexiRule does not expose Frappe's native `distinct` support in list queries.

This report outlines the complete architecture of both engines, details every capability gap and behavioral bug, and provides a prioritized, low-complexity roadmap to bring FlexiRule to full parity and compliance with Frappe's security and querying models.

---

## 2. Frappe Query API Architecture

In Frappe, querying the database is orchestrated primarily via two entry points in `frappe/__init__.py`:
- `frappe.get_list()`: Executes database queries with role-level, user-level, sharing, and field-level permission checks.
- `frappe.get_all()`: A wrapper around `get_list()` that forces permission bypass and defaults to returning all matching records.

Both APIs instantiate and delegate the compilation of queries to `frappe.model.db_query.DatabaseQuery`. Contrary to modern ORMs, Frappe does not use its Query Builder (PyPika-based) to compile `get_list` or `get_all` queries; instead, it compiles queries via recursive string and list manipulation inside Python and runs them via raw SQL execution.

### Key Source Files & Locations:
*   **Entry Points**: `frappe/__init__.py` (`get_list` at line 2010, `get_all` at line 2033)
*   **Query Compilation**: `frappe/model/db_query.py` (`DatabaseQuery` class at line 71)
*   **Permission Evaluation**: `frappe/permissions.py` (`has_permission` at line 77, `has_child_permission` at line 763)
*   **Filter Parsing**: `frappe/utils/data.py` (`get_filter` at line 1892)

---

## 3. Complete Call Graph

The following call graph traces the complete execution path from a developer calling `frappe.get_list` down to the final database execution.

```
frappe.get_all(doctype, **kwargs)
  │ (sets ignore_permissions=True, limit_page_length=0)
  ▼
frappe.get_list(doctype, **kwargs)
  │
  ▼
frappe.model.db_query.DatabaseQuery(doctype).execute(**kwargs)
  │
  ├──► [If ignore_permissions=False] self.check_read_permission(doctype)
  │      │
  │      ▼
  │    frappe.permissions.has_permission(doctype, ptype="read")
  │      │
  │      └─► [If doctype is child table] has_child_permission(child_doctype, parent_doctype)
  │
  ├──► self.get_table_columns() (Fetches columns from metadata schema)
  │
  └──► self.build_and_run()
         │
         ├──► self.prepare_args()
         │      │
         │      ├──► self.parse_args()
         │      │      │ (Resolves JSON filters/fields; maps Link and Table dot-notation)
         │      │      └─► self.append_link_table(linked_doctype, fieldname)
         │      │
         │      ├──► self.sanitize_fields()
         │      │      │ (Uses sqlparse AST checking to block subqueries, union, and functions)
         │      │      └─► _check_sql_token(statement)
         │      │
         │      ├──► self.extract_tables()
         │      │      │ (Extracts table names from fields)
         │      │      └─► self.append_table(table_name)
         │      │
         │      ├──► self.build_conditions()
         │      │      │
         │      │      ├──► self.build_filter_conditions()
         │      │      │      └─► self.prepare_filter_condition(f)
         │      │      │            ├──► frappe.utils.get_filter(self.doctype, f)
         │      │      │            │      │ (Normalizes filters; auto-detects child table field owner)
         │      │      │            │      └─► make_filter_tuple(doctype, key, value)
         │      │      │            └──► self.append_table(child_table_name)
         │      │      │
         │      │      └──► [If ignore_permissions=False] self.build_match_conditions()
         │      │             │ (Builds SQL restrictions for Role, Owner, Share, and User Permissions)
         │      │             └─► self.get_share_condition() / self.add_user_permissions()
         │      │
         │      ├──► self.apply_fieldlevel_read_permissions()
         │      │      │ (Removes fields from projection list that the user has no role-rights to see)
         │      │      └─► self.remove_field(idx)
         │      │
         │      ├──► [Table joins compilation]
         │      │      ├──► Left-joins child tables on:
         │      │      │    `child.parenttype = doctype AND child.parent = parent.name`
         │      │      └──► Left-joins link tables on:
         │      │           `link_alias.name = parent.fieldname`
         │      │
         │      ├──► self.set_order_by() / self.validate_order_by_and_group_by()
         │      │      └─► (Enforces SQL injection blacklist on order/group-by clauses)
         │      │
         │      └─► Return prepared args (fields, tables, conditions, order_by, group_by)
         │
         ├──► self.add_limit() (Appends offset and length limit clauses)
         │
         ├──► [Interpolate raw SQL string]
         │      `select {fields} from {tables} {conditions} {group_by} {order_by} {limit}`
         │
         └──► frappe.db.sql(query, as_dict, debug, ...)
                │
                └──► [Database Engine Driver execution]
                     (mariadb/database.py or postgres/database.py execute method)
```

---

## 4. Query Execution Pipeline

The database query is processed in several distinct phases before execution:

1.  **Instantiation & Permission Gate**:
    *   File: `frappe/model/db_query.py` (`__init__` and `execute`)
    *   `DatabaseQuery(doctype)` is initialized. If permissions are checked, it validates reader permission on the target DocType.

2.  **Argument Normalization (`parse_args`)**:
    *   File: `frappe/model/db_query.py` (`parse_args`)
    *   Dotted-path strings are parsed. Link fields are assigned unique table aliases (e.g. ``` `tabDocType_1` ```). Child tables are rewritten to their database table syntax (e.g. ``` `tabChild DocType`.`fieldname` ```). Dict filters are transformed into standard lists of filter tuples.

3.  **Sanitization Check (`sanitize_fields`)**:
    *   File: `frappe/model/db_query.py` (`sanitize_fields`)
    *   Fields are processed using `sqlparse`. If a field contains subqueries, comments, or blacklisted functions (`concat`, `if`, `coalesce`, `sleep`), execution halts with `frappe.DataError: Use of sub-query or function is restricted`.

4.  **Table Extraction (`extract_tables`)**:
    *   File: `frappe/model/db_query.py` (`extract_tables`)
    *   Scans the projection list (`self.fields`) to detect referenced tables and appends them to the internal `self.tables` tracking array.

5.  **Filter & Match Conditions Compilation (`build_conditions`)**:
    *   File: `frappe/model/db_query.py` (`build_conditions`, `prepare_filter_condition`)
    *   Each filter is evaluated using `get_filter`. If a filter doctype is not in `self.tables`, `self.append_table()` is triggered.
    *   The system builds standard conditional expressions (e.g., `ifnull(column, fallback) operator value`).
    *   `build_match_conditions()` appends SQL where constraints enforcing role-rights, user sharing permissions, and DocShare rules.

6.  **SQL Generation (`prepare_args`)**:
    *   File: `frappe/model/db_query.py` (`prepare_args`)
    *   Primary and child/link tables are joined. Projection fields are quoted. Order-by and group-by clauses are appended and checked.
    *   The system formats the raw SQL statement.

7.  **Database Execution**:
    *   File: `frappe/database/database.py` (`sql`)
    *   Runs the raw SQL query on the active database driver (MariaDB or PostgreSQL) and returns the list of flat dictionaries (or tuples).

---

## 5. Supported Features Matrix

The following table lists the querying features supported by Frappe’s `DatabaseQuery` along with the source-code proof:

| Feature Category | Feature | Supported | Source Code Evidence & Notes |
| :--- | :--- | :---: | :--- |
| **Fields** | Normal Fields | ✅ | `db_query.py:execute` — Default projection. |
| | Link Fields | ✅ | `db_query.py:parse_args` (lines 359–370) — Resolved using `append_link_table()`. |
| | Dynamic Links | ✅ | `db_query.py:get_table_columns()` / `db_query.py:prepare_filter_condition`. |
| | Aliases | ✅ | `db_query.py:parse_args` — Splits field on `" as "` (line 357). |
| | SQL Expressions | ⚠ Partial | `db_query.py:sanitize_fields` — Allowed if they avoid blacklisted operators/functions. |
| | Aggregates (COUNT/SUM/AVG/MIN/MAX) | ✅ | Allowed in select projection list, and supported natively in `db_query.py:extract_tables`. |
| | DISTINCT | ✅ | `db_query.py:build_and_run` (line 233) — Prepends `distinct` to the field list. |
| | CONCAT / CASE / IF | ❌ | `db_query.py:sanitize_fields` (lines 405–420) — Explicitly blacklisted to prevent injection. |
| | IFNULL | ✅ | `db_query.py:prepare_filter_condition` — Permitted and generated automatically. |
| **Filters** | Standard (=, !=, >, <, >=, <=) | ✅ | `utils/data.py:get_filter` (line 1928) — Standard valid operators. |
| | LIKE / NOT LIKE | ✅ | `utils/data.py:get_filter` / `db_query.py:prepare_filter_condition` (line 930) — Escapes `%`. |
| | BETWEEN | ✅ | `db_query.py:prepare_filter_condition` (line 890) / `db_query.py:get_between_date_filter`. |
| | IN / NOT IN | ✅ | `db_query.py:prepare_filter_condition` (line 847) — Parses lists and comma-separated strings. |
| | IS / IS NOT | ✅ | `utils/data.py:get_filter` / `db_query.py:prepare_filter_condition` (line 910) — Maps `set` and `not set`. |
| | EXISTS / NOT EXISTS | ❌ | Not in `valid_operators` of `utils/data.py:get_filter` (line 1928). |
| | Timespans / Tree Hierarchies | ✅ | `db_query.py:prepare_filter_condition` (line 875) — Normalizes timespans and nested tree sets. |
| | Flat AND/OR groups | ✅ | `db_query.py:build_conditions` — Maps AND to `filters` and grouped ORs to `or_filters`. |
| | Recursive Nested AND/OR | ❌ | Not supported. `DatabaseQuery` only handles flat lists of `filters` and `or_filters`. |
| **Ordering** | Multiple Order Clauses | ✅ | `db_query.py:set_order_by` — Supported by passing a comma-separated string. |
| | Random Ordering | ✅ | Passes `rand()` or `random()` directly to order by clause. |
| | NULL Ordering | ✅ | Standard SQL null order rules apply. |
| **Pagination**| limit / page_length / start / offset | ✅ | `db_query.py:execute` (lines 135–140) and `db_query.py:add_limit`. |

---

## 6. Child DocType Investigation

A deep investigation of whether and how Frappe supports querying Child DocTypes directly vs. implicitly yielded the following code-backed conclusions:

### Q1: Can `get_list()` query a Child DocType directly?
*   **Answer**: **Yes, but with strict parent permission requirements.**
*   **Proof**:
    *   When calling `frappe.get_list("Sales Invoice Item", ignore_permissions=False)`, `DatabaseQuery.execute()` calls `check_read_permission("Sales Invoice Item")` (line 567).
    *   This delegates to `frappe.has_permission("Sales Invoice Item", ptype="read")`.
    *   In `frappe/permissions.py:has_permission()` (line 120):
        ```python
        if frappe.is_table(doctype):
            return has_child_permission(doctype, ptype, doc, user, raise_exception, parent_doctype, debug=debug)
        ```
    *   In `frappe/permissions.py:has_child_permission()`, if `parent_doctype` is not provided and cannot be inferred from a loaded child document, the check logs a warning and returns `False` (line 783):
        ```python
        if not parent_doctype:
            push_perm_check_log(_("Please specify a valid parent DocType for {0}").format(frappe.bold(child_doctype)), debug=debug)
            return False
        ```
    *   Therefore, running `frappe.get_list("Sales Invoice Item")` raises a `frappe.PermissionError` unless:
        1.  The user runs it with `ignore_permissions=True` (or via `get_all()`).
        2.  The developer explicitly passes `parent_doctype="Sales Invoice"` and the user has read access to the parent document.

### Q2: Can `get_all()` query a Child DocType?
*   **Answer**: **Yes, fully and without constraints.**
*   **Proof**:
    *   `get_all()` is defined in `frappe/__init__.py` (line 2033). It sets `kwargs["ignore_permissions"] = True`.
    *   Since permissions are ignored, `DatabaseQuery.execute()` bypasses `check_read_permission()` and queries the child table directly from the database (e.g. ```select * from `tabSales Invoice Item````), bypassing any permission gates.

### Q3: Can filters reference child tables? (e.g., `Sales Invoice` with filters `items.item_code = X`)
*   **Answer**: **Yes, fully supported.**
*   **Proof**:
    *   If a filter specifies a child doctype field name directly, or if the filter is nested as a list of lists:
    *   In `frappe/utils/data.py:get_filter()` (lines 1956–1965), if the field does not belong to the primary parent doctype, Frappe inspects the parent's table fields:
        ```python
        if f.doctype and (f.fieldname not in default_fields + optional_fields + child_table_fields):
            meta = frappe.get_meta(f.doctype)
            if not meta.has_field(f.fieldname):
                for df in meta.get_table_fields():
                    if frappe.get_meta(df.options).has_field(f.fieldname):
                        f.doctype = df.options
                        break
        ```
    *   If matched, `f.doctype` is rewritten to the child DocType.
    *   In `frappe/model/db_query.py:prepare_filter_condition()` (lines 780–782), if the child table is not in `self.tables`, it is automatically appended:
        ```python
        tname = "`tab" + f.doctype + "`"
        if tname not in self.tables:
            self.append_table(tname)
        ```
    *   In `prepare_args()` (lines 277–280), all tables in `self.tables[1:]` (which now includes the child table) are automatically left-joined to the parent on their parent-child links.

### Q4: Does Frappe automatically JOIN child tables?
*   **Answer**: **Yes, implicitly on detection.**
*   **Proof**:
    *   If a child table field is specified in `fields` (e.g. `items.item_code`) or in `filters` (e.g. `item_code`), Frappe's metadata resolution detects the child table relationship.
    *   The child table name is added to `self.tables`.
    *   In `db_query.py:prepare_args()`, the system loops through all child tables in `self.tables[1:]` and appends a `LEFT JOIN` clause:
        ```python
        for child in self.tables[1:]:
            parent_name = cast_name(f"{self.tables[0]}.name")
            args.tables += f" {self.join} {child} on ({child}.parenttype = {frappe.db.escape(self.doctype)} and {child}.parent = {parent_name})"
        ```

### Q5: Can fields reference child table fields? (e.g., `fields=["name", "items.item_code"]`)
*   **Answer**: **Yes, fully supported.**
*   **Proof**:
    *   In `db_query.py:parse_args()` (lines 359–374), fields with a `.` are parsed.
    *   If the prefix (e.g., `items`) is identified as a Table field, the projection field is rewritten to point to the child database table:
        ```python
        field = f"`tab{linked_doctype}`.`{fieldname}`"
        ```
    *   During `db_query.py:extract_tables()`, the system extracts ``` `tabSales Invoice Item` ``` from the fields list and appends it to `self.tables`, causing an automatic `LEFT JOIN` during SQL compilation.

### Q6: Performance & Row Duplication
*   **Answer**: **Frappe does NOT perform any ORM-level deduplication or child-row nesting.**
*   **Proof**:
    *   When joining a parent table with a child table, SQL returns multiple rows for a single parent (one per child record).
    *   Frappe executes the raw SQL query and returns a flat list of dictionaries directly from `frappe.db.sql()`.
    *   No post-processing or nested structure conversion is performed on the result list.
    *   If a parent table has 5 child rows, querying `get_list` with child fields or filters returns 5 duplicate parent row dictionaries.
    *   To prevent this, the user must explicitly pass `distinct=True` or `group_by="name"`.

---

## 7. Parent/Child Join Behavior

The actual SQL generated by `DatabaseQuery` when joining child tables is highly specific.

For a query on parent `Sales Invoice` with fields `["name", "items.item_code"]` and filters `[["items.item_code", "=", "ITEM-001"]]`, the generated SQL tables section is built in `prepare_args()` as:

```sql
SELECT
    `tabSales Invoice`.`name`,
    `tabSales Invoice Item`.`item_code`
FROM
    `tabSales Invoice`
LEFT JOIN
    `tabSales Invoice Item` ON (
        `tabSales Invoice Item`.parenttype = 'Sales Invoice'
        AND `tabSales Invoice Item`.parent = `tabSales Invoice`.name
    )
WHERE
    `tabSales Invoice Item`.`item_code` = 'ITEM-001'
```

### Metadata and Join Conditions:
- **Child Tables Join Condition**: `child_table.parenttype = {parent_doctype} AND child_table.parent = parent_table.name`
- **Link Tables Join Condition**: `link_table_alias.name = parent_table.link_fieldname`

---

## 8. Permission Model

Frappe applies fine-grained permissions depending on which API is utilized:

```
┌────────────────────────────────────────────────────────┐
│                      get_list()                        │
└───────────────────────────┬────────────────────────────┘
                            │
              Is ignore_permissions=True?
               ├── Yes ──► Bypass permissions
               └── No ───► Check Read Rights on DocType
                             │
                     Check DocShare / Row Sharing
                             │
                     Apply User Permissions Filters
                             │
                     Apply Role Match Conditions
                             │
                     Apply Field-Level Read Permissions
                             │
                             ▼
                    Return Filtered Records
```

### 1. `get_list()` vs. `get_all()`:
*   `get_list()`: Enforces full, fine-grained permission logic by default.
*   `get_all()`: Programmatically forces `ignore_permissions = True`. Bypasses doc-level, row-level, sharing, and field-level permission checks.

### 2. Database API vs. Query Builder:
*   **Database API (`frappe.db.get_value`, `frappe.db.exists`)**: Operates entirely at system-level. No permission checks are ever executed.
*   **Query Builder (PyPika)**: Low-level database compiler. It has no integration with Frappe’s permissions, sharing, or metadata rules. The developer is fully responsible for security.

---

## 9. Query Builder Comparison

Frappe's Query Builder provides rich SQL generation capabilities that are unavailable through the standard `frappe.get_list` interface.

| Capability | frappe.get_list() | Frappe Query Builder |
| :--- | :---: | :---: |
| **SQL compilation** | Raw string formatting & interpolation (`prepare_args`) | Object-oriented AST generation (PyPika) |
| **Custom Joins** | ❌ Only implicit child/link left-joins allowed | ✅ Inner, Right, Full Outer, Cross joins on custom conditions |
| **Set Operations** | ❌ Blocked (`UNION`, `INTERSECT` are blacklisted) | ✅ Full support for `UNION`, `INTERSECT`, `EXCEPT` |
| **Arbitrary Functions**| ❌ Blocked (`CONCAT`, `CASE`, `IF`, `COALESCE` are blacklisted) | ✅ Supports all database functions |
| **Subqueries** | ❌ Blocked (AST checking raises restricted error) | ✅ Supports nested subqueries anywhere |
| **Complex Logic** | ❌ Flat `filters` and `or_filters` only | ✅ Recursive, deep boolean logic trees (`&`, `\|`) |
| **Common Table Expressions** | ❌ Unsupported | ✅ Full support for CTEs (`WITH` clauses) |

---

## 10. FlexiRule Architecture

FlexiRule implements its query capability via the `QueryRecordsHandler` class in `flexirule/ruleflow/core/action_handlers/query_records.py`.

### Architecture Diagram:

```
                 Rule / Flow Evaluation Context
                                │
                                ▼
         QueryRecordsHandler.execute(action, context, engine)
                                │
                  [can_ignore_permissions check]
                                │
                     [apply_input_mapping]
                                │
                      Dispatch based on Mode
                                │
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                        ▼
   Query List               Query Doc               Exist Record /
 (frappe.get_list)       (frappe.get_doc)        Aggregates / Group By
                                                     (frappe.get_all)
```

### Execution Flow & Parsing Details:
1.  **Entry**: `execute(action, context, engine)` is invoked.
2.  **Permission Gate Check**: `can_ignore_permissions` checks if `ignore_permissions` is configured and audits the reason.
3.  **Input Mapping**: Resolves contextual values and mappings from Pinia context to filters.
4.  **Filter Normalization**: Parses standard lists/dicts, resolving timespans, wildcards, and UI operators (e.g. `starts with` -> `like`, `Between` -> `between`).
5.  **Execution Modes**:
    *   `Query List` calls `frappe.get_list`.
    *   `Query Doc` calls `frappe.get_doc` or `frappe.get_cached_doc`.
    *   `Exist Record`, `Count`, `Sum`, `Average`, `Min`, `Max`, and `Group By` call `frappe.get_all`.
6.  **Return**: Maps the output to a context variable based on `mutation_mode`.

---

## 11. Feature-by-Feature Comparison

The table below contrasts the actual query capabilities supported by Frappe vs. FlexiRule's current implementation:

| Capability | Frappe Query API | FlexiRule Query Records | Parity Status |
| :--- | :---: | :---: | :---: |
| **Normal Fields** | ✅ | ✅ | **Full Parity** |
| **Link Fields Join** | ✅ | ✅ | **Full Parity** |
| **Child DocField Join** | ✅ | ✅ | **Full Parity** |
| **Query Child DocType Directly**| ✅ | ❌ | **Gaps / Incorrect Behavior** |
| **Dotted Path Filters** | ✅ | ✅ | **Full Parity** |
| **Automatic Joins** | ✅ | ✅ | **Full Parity** |
| **Deduplication / DISTINCT** | ✅ | ❌ | **Missing** |
| **Aggregate Operations** | ✅ | ✅ | **Supported (with Security Gaps)** |
| **Group By Operations** | ✅ | ✅ | **Supported (with Security Gaps)** |
| **Nested Filter Groups** | ❌ | ❌ | **Full Parity** (Both restricted) |
| **SQL Inject Protection** | ✅ | ✅ | **Full Parity** |
| **Field-Level Permissions** | ✅ | ⚠ Partial | **Security Risk** (Bypassed in aggregates) |
| **Row-Level User Permissions** | ✅ | ⚠ Partial | **Security Risk** (Bypassed in aggregates) |
| **DocShare Permissions** | ✅ | ⚠ Partial | **Security Risk** (Bypassed in aggregates) |

---

## 12. Missing Features

### 1. DISTINCT / Projection Deduplication
*   **Gap**: When parent-child table joins are performed (e.g. selecting or filtering on child table fields), Frappe returns multiple parent rows. To prevent this, Frappe allows passing `distinct=True`. FlexiRule's `_query_list` mode does not extract or pass `distinct` from the configuration to `get_list()`.
*   **Impact**: Querying lists with child table filters results in duplicate parent records, with no way for a rule builder to clean or deduplicate the records in the UI.

### 2. Direct Child DocType Query with Permissions
*   **Gap**: Programmatic querying of Child DocTypes requires passing the `parent_doctype` parameter to check permissions on parent records. FlexiRule's `_query_list` method does not forward `parent_doctype` to `get_list`.
*   **Impact**: Querying a Child DocType with permissions enabled fails with `frappe.PermissionError`.

---

## 13. Bugs and Behavioral Differences

### 1. Critical Permissions Bypass in Aggregates and Group-Bys
*   **File**: `flexirule/ruleflow/core/action_handlers/query_records.py`
*   **Methods**: `_count_records`, `_aggregate`, `_group_by`
*   **Code Location**:
    ```python
    rows = frappe.get_all(
        reference_doctype,
        filters=filters,
        or_filters=or_filters,
        fields=[...],
        ignore_permissions=ignore_permissions,
    )
    ```
*   **The Bug**: `frappe.get_all()` explicitly overrides `kwargs["ignore_permissions"] = True`.
*   **Result**: Even if the action is configured with `ignore_permissions=0` (meaning permissions must be enforced) and FlexiRule verifies reader access using `frappe.has_permission(reference_doctype, "read")`, the subsequent `get_all` execution completely ignores role-matching, document sharing constraints, owner restrictions, and user permissions. Users can retrieve aggregate metrics and counts across records they are not permitted to see.
*   **Security of Reports**: For `Query Report`, because report execution does not support an `ignore_permissions` flag (and report permissions are strictly audited/enforced by Frappe's report rendering engine), report permissions can never be bypassed, even if `ignore_permissions` is passed. Thus, report permissions can never be bypassed, while `ignore_permissions` only applies to Query List/Database operations.

---

## 14. Recommended Improvements

### Recommendation 1: Replace `frappe.get_all` with `frappe.get_list` in Metrics, Aggregates, and Group By Modes
*   **Evidence / Reason**: `frappe.get_all` hardcodes the bypass of permission rules. By replacing it with `frappe.get_list` and explicitly setting `limit_page_length=0`, we maintain high performance while strictly enforcing row-level, sharing, and field-level permissions.
*   **Current Implementation**:
    ```python
    rows = frappe.get_all(
        reference_doctype,
        filters=filters,
        or_filters=or_filters,
        fields=["count(name) as _count"],
        ignore_permissions=ignore_permissions,
    )
    ```
*   **Proposed Implementation**:
    ```python
    rows = frappe.get_list(
        reference_doctype,
        filters=filters,
        or_filters=or_filters,
        fields=["count(name) as _count"],
        limit_page_length=0,
        ignore_permissions=ignore_permissions,
    )
    ```
*   **Priority**: **Critical**
*   **Complexity**: **Small**

### Recommendation 2: Map and Pass `parent_doctype` for Direct Child Table List Queries
*   **Evidence / Reason**: Querying child DocTypes directly with permissions checked requires passing the `parent_doctype` to `has_child_permission`.
*   **Current Implementation**:
    ```python
    kwargs = {
        "doctype": reference_doctype,
        "filters": filters,
        "fields": fields,
        "limit_page_length": limit,
        "order_by": order_by,
        "ignore_permissions": ignore_permissions,
    }
    ```
*   **Proposed Implementation**:
    ```python
    kwargs = {
        "doctype": reference_doctype,
        "filters": filters,
        "fields": fields,
        "limit_page_length": limit,
        "order_by": order_by,
        "ignore_permissions": ignore_permissions,
    }
    # Check if target doctype is a child table, extract parent
    if frappe.is_table(reference_doctype):
        parent_dt = config.get("parent_doctype") or reference_doctype
        kwargs["parent_doctype"] = parent_dt
    ```
*   **Priority**: **High**
*   **Complexity**: **Small**

### Recommendation 3: Implement `distinct` Support in List Queries
*   **Evidence / Reason**: Support deduplicating projection rows on left-joins.
*   **Current Implementation**:
    No `distinct` parameter is extracted from `config` or passed to `get_list`.
*   **Proposed Implementation**:
    ```python
    kwargs = {
        "doctype": reference_doctype,
        "filters": filters,
        "fields": fields,
        "limit_page_length": limit,
        "order_by": order_by,
        "ignore_permissions": ignore_permissions,
        "distinct": bool(config.get("distinct")),
    }
    ```
*   **Priority**: **Medium**
*   **Complexity**: **Small**

---

## 15. Prioritized Action Plan

To ensure security compliance, parity, and feature robustness, the following execution roadmap is recommended:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                               ACTION PLAN                                    │
├───────┬─────────────────────────────────────────────────┬──────────┬─────────┤
│ Stage │ Action Item / Description                       │ Priority │ Effort  │
├───────┼─────────────────────────────────────────────────┼──────────┼─────────┤
│   1   │ Replace `get_all` with `get_list` for:          │ Critical │  Small  │
│       │ - `_count_records`                              │          │         │
│       │ - `_aggregate`                                  │          │         │
│       │ - `_group_by`                                   │          │         │
│       │ This eliminates the aggregate permission bypass│          │         │
├───────┼─────────────────────────────────────────────────┼──────────┼─────────┤
│   2   │ Pass `parent_doctype` parameter to `get_list`   │   High   │  Small  │
│       │ in `_query_list` when querying child tables.    │          │         │
├───────┼─────────────────────────────────────────────────┼──────────┼─────────┤
│   3   │ Extract and map `distinct` key from frontend    │  Medium  │  Small  │
│       │ configuration to `frappe.get_list`.             │          │         │
└───────┴─────────────────────────────────────────────────┴──────────┴─────────┘
```
