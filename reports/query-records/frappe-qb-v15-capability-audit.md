# Frappe v15 `frappe.qb.get_query` Capability Audit Report

## Executive Summary

Before refactoring FlexiRule's Query Records backend and frontend contracts, a comprehensive, evidence-backed backend audit of `frappe.qb.get_query()` was conducted against the repository's target Frappe v15 test environment (`test_site`).

An automated backend test suite (`flexirule/ruleflow/tests/test_frappe_qb_capabilities.py`) was constructed and executed. Every documented capability was systematically tested to verify:
1. Whether the API accepts the syntax
2. Whether SQL is generated successfully
3. Whether the query executes and produces the expected data semantics and row structures

---

## 1. Installed Environment Specifications

* **Frappe Version:** `15.121.1`
* **Frappe Repository Commit:** `8f801ade016078685c3165c96e38f84f249f5309` (branch: `version-15`)
* **Python Version:** `3.12.13`
* **Database Engine:** `MariaDB`
* **Database Version:** `10.11.14-MariaDB-0ubuntu0.24.04.1`
* **Query Builder Implementation Files:**
  * `frappe/query_builder/utils.py` (Defines `get_query()` entry point and patches `run()` / `walk()`)
  * `frappe/database/query.py` (Defines `Engine`, `Permission`, `ChildQuery`, `DynamicTableField`, `parse_fields`, `apply_filters`)
  * `frappe/database/operator_map.py` (Defines operator mappings for SQL generation)
  * `frappe/query_builder/builder.py` (Database-specific builder overrides for MariaDB & Postgres)

---

## 2. Capability Audit Results by Category

### 2.1 Basic Query & Fields Selection
* **`frappe.qb.get_query("DocType")`**: Generates `SELECT name FROM tabDocType`. When fields are omitted (`fields=None`), default field selection returns `name`.
* **Explicit Fields (`fields=["name", "status"]`)**: Supported and returns selected fields.
* **Comma-Separated String Fields (`fields="name, status"`)**: Supported; `Engine` splits comma-separated strings into field lists.
* **All Fields (`fields="*"`)**: Supported; returns all document schema columns.
* **Field Aliases (`fields=["name as doc_id"]`)**: Supported; returned dictionary keys match the alias name (`doc_id`).

### 2.2 Execution Modes & Result Formats
* **`query.run(as_dict=True)`**: Supported; returns list of dictionaries.
* **`query.run(as_list=True)`**: Supported; returns tuple/list of tuples.
* **`query.run(pluck=True)`**: Supported; returns a flat list of scalar field values. Requires a single field in the selection.
* **`query.run(as_iterator=True)`**: Passed down to `frappe.db.sql()`. Requires buffered cursor compatibility in pymysql.

### 2.3 Filter Syntax & Logical Operations
* **Dict Equality (`filters={"status": "Open"}`)**: Supported.
* **Dict Operator Form (`filters={"enabled": [">", 0]}`)**: Supported.
* **List Form (`filters=[["status", "=", "Open"]]`)**: Supported.
* **Multiple Filters (AND behavior)**: Supported by combining elements in list or dict.
* **Infix String `"or"` in List Filters (`filters=[["status", "=", "Open"], "or", ["status", "=", "Pending"]]`)**: **UNSUPPORTED / BROKEN.** `Engine.apply_filters` parses any string element in a filter list as `{"name": str}`, converting `"or"` into `WHERE name = 'or'`, which returns 0 results.
* **Logical OR / Complex Groups**: Must be passed as Pypika `Criterion` objects (e.g. `(t.status == "Open") | (t.status == "Pending")`).

### 2.4 Filter Operators
* **Standard Comparison Operators (`=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `not like`, `in`, `not in`)**: Fully SUPPORTED and verified against test data.
* **Null / Set Operators (`is`, `is set`, `is not set`)**: Fully SUPPORTED.
* **Tree / Nested Set Operators (`descendants of`, `ancestors of`)**: **UNSUPPORTED** directly in `frappe.qb.get_query`. Generates operator lookup exceptions in `Engine`.

### 2.5 Link-Field Traversal
* **Selecting Linked Fields (`fields=["name", "target_link.territory"]`)**: Fully SUPPORTED. Automatically generates `LEFT JOIN tabQB Test Target ON ...`.
* **Filtering Linked Fields (`filters={"target_link.territory": "North"}`)**: Fully SUPPORTED.
* **Linked Field Aliases (`fields=["target_link.territory as dest_region"]`)**: Fully SUPPORTED.
* **Ordering by Dotted Linked Fields (`order_by="target_link.territory asc"`)**: **UNSUPPORTED**. Generates `pymysql.err.OperationalError: (1054, "Unknown column 'tabQB Test Parent.target_link.territory' in 'ORDER BY'")` because `order_by` string does not resolve the join alias.

### 2.6 Child Table Traversal
* **Selecting Dotted Child Fields (`fields=["name", "items.item_code"]`)**: Fully SUPPORTED. Generates `LEFT JOIN tabQB Test Child`. Duplicates parent rows in the result set for each matching child row.
* **Filtering Dotted Child Fields (`filters={"items.item_code": "ITEM-001"}`)**: Fully SUPPORTED.
* **Distinct Parent Records (`distinct=True`)**: Fully SUPPORTED. Eliminates duplicate parent rows when filtering through child tables.
* **Structured Child Fetching (`fields=["name", {"items": ["item_code", "qty"]}]`)**: Fully SUPPORTED. `Engine` instantiates `ChildQuery`, executing secondary queries and embedding child record lists directly into each parent dictionary (`row["items"] = [...]`).

### 2.7 Aggregation & Scalar Functions
* **Documented Dict Aggregation Syntax (`fields=[{"COUNT": "name", "as": "total"}]`)**: **DOCUMENTED BUT UNSUPPORTED.** `Engine.parse_fields` interprets dictionary objects in `fields` as child table queries. Since `"COUNT"` is not a table field, it raises `AttributeError: 'NoneType' object has no attribute 'fieldtype'`.
* **Working Aggregation Syntax**:
  1. SQL string expressions: `fields=["count(name) as total_count"]`, `fields=["sum(enabled) as sum_enabled"]`
  2. Pypika / Frappe QB function objects: `from frappe.query_builder.functions import Count, Sum`
* **Documented Dict Scalar Function Syntax (`fields=[{"IFNULL": ...}]`)**: **UNSUPPORTED** for the same reason (interpreted as child query -> raises `AttributeError`).
* **Pypika / Frappe QB Functions (`Now()`, `Ifnull()`, `Concat()`)**: Fully SUPPORTED via `frappe.query_builder.functions`.

### 2.8 Order By, Group By, Pagination, Distinct
* **`order_by="status asc, name desc"`**: Fully SUPPORTED for standard fields.
* **`group_by="status"`**: Fully SUPPORTED.
* **`limit=10, offset=10`**: Fully SUPPORTED. Passed to Pypika query builder.
* **`distinct=True`**: Fully SUPPORTED.

### 2.9 Permissions & User Context
* **`ignore_permissions=True` / `user="..."` as kwargs to `frappe.qb.get_query()`**: **UNSUPPORTED.** `Engine.get_query()` does not take `ignore_permissions` or `user` kwargs and raises `TypeError: Engine.get_query() got an unexpected keyword argument`.
* **Permission Enforcement**: In Frappe v15, permission checking on query builder objects is handled separately via `frappe.database.query.Permission.check_permissions(query, user=...)`.

### 2.10 Debug & SQL Inspection
* **`query.get_sql()`**: Fully SUPPORTED. Returns the raw compiled SQL string.
* **`query.run(debug=True)`**: Fully SUPPORTED. Prints execution timing and SQL to stdout/logs.

### 2.11 Pypika Objects Integration
* **Pypika Fields in `fields=[...]`**: Fully SUPPORTED (e.g. `Field("parent_title")`).
* **Pypika Criterion in `filters=...`**: Fully SUPPORTED (e.g. `(Field("enabled") == 1)`).

### 2.12 Record Locking
* **`for_update=True`, `skip_locked=True`, `wait=False`**: Fully SUPPORTED. Generates `FOR UPDATE SKIP LOCKED` SQL clauses.

### 2.13 Input Validation & Security
* **Invalid Field Identifiers**: Raises database `OperationalError` on query execution. `frappe.qb.get_query()` relies on MariaDB SQL compilation for field name validation.

---

## 3. Comprehensive Capability Matrix

| Capability | Tested Syntax / Form | Frappe Support Status | Verified Semantics | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Basic Query** | `frappe.qb.get_query("DocType")` | **SUPPORTED** | Returns `name` by default |
| **Explicit Fields** | `fields=["name", "status"]` | **SUPPORTED** | Returns requested keys |
| **Comma Fields** | `fields="name, status"` | **SUPPORTED** | Splits comma string |
| **Asterisk Fields** | `fields="*"` | **SUPPORTED** | Selects all columns |
| **Field Aliases** | `fields=["name as doc_id"]` | **SUPPORTED** | Alias key returned |
| **`as_dict=True`** | `query.run(as_dict=True)` | **SUPPORTED** | List of dicts |
| **`as_list=True`** | `query.run(as_list=True)` | **SUPPORTED** | List of tuples |
| **`pluck=True`** | `query.run(pluck=True)` | **SUPPORTED** | Flat list of values | Requires single field |
| **Dict Filters** | `filters={"status": "Open"}` | **SUPPORTED** | Exact match |
| **Dict Op Filters** | `filters={"qty": [">", 0]}` | **SUPPORTED** | Evaluates operator |
| **List Filters** | `filters=[["status", "=", "Open"]]` | **SUPPORTED** | Standard 3-tuple |
| **Infix String OR** | `filters=[..., "or", ...]` | **UNSUPPORTED** | Returns 0 results | Parsed as `name = 'or'` |
| **Pypika OR** | `filters=(t.a == 1) \| (t.b == 2)` | **SUPPORTED** | Generates SQL `OR` | Core mechanism for OR logic |
| **Comparison Ops** | `=`, `!=`, `>`, `<`, `>=`, `<=` | **SUPPORTED** | Evaluated correctly |
| **Pattern Ops** | `like`, `not like`, `in`, `not in` | **SUPPORTED** | Evaluated correctly |
| **Null Ops** | `is`, `is set`, `is not set` | **SUPPORTED** | Evaluated correctly |
| **Tree Ops** | `descendants of`, `ancestors of` | **UNSUPPORTED** | Raises KeyError | Not in operator map |
| **Link Field Select** | `fields=["link.field"]` | **SUPPORTED** | Auto LEFT JOIN |
| **Link Field Filter** | `filters={"link.field": "val"}` | **SUPPORTED** | Filters joined table |
| **Link Field Order** | `order_by="link.field asc"` | **UNSUPPORTED** | Raises OperationalError | Alias unmapped in order_by |
| **Child Dotted Field**| `fields=["items.item_code"]` | **SUPPORTED** | Auto LEFT JOIN | Duplicates parent rows |
| **Child Field Filter**| `filters={"items.item_code": "x"}`| **SUPPORTED** | Filters child table |
| **Distinct Child** | `distinct=True` | **SUPPORTED** | Deduplicates parents |
| **Structured Child** | `fields=[{"items": ["a", "b"]}]` | **SUPPORTED** | Nested child dict list | Runs sub-query per parent |
| **Dict Aggregation** | `fields=[{"COUNT": "name"}]` | **UNSUPPORTED** | Raises AttributeError | Interp. as child query |
| **String Aggregation**| `fields=["count(name) as total"]`| **SUPPORTED** | SQL COUNT generated |
| **Pypika Aggregation**| `fields=[Count("name")]` | **SUPPORTED** | SQL COUNT generated |
| **Dict Functions** | `fields=[{"IFNULL": ...}]` | **UNSUPPORTED** | Raises AttributeError | Interp. as child query |
| **Pypika Functions** | `fields=[Now(), Ifnull()]` | **SUPPORTED** | Generates SQL functions |
| **Order By** | `order_by="status asc, name desc"`| **SUPPORTED** | Standard order applied |
| **Group By** | `group_by="status"` | **SUPPORTED** | Generates GROUP BY |
| **Pagination** | `limit=10, offset=10` | **SUPPORTED** | LIMIT / OFFSET set |
| **`ignore_permissions`**| `get_query(..., ignore_permissions=True)` | **UNSUPPORTED** | Raises TypeError | Kwarg not in Engine |
| **`user` Context** | `get_query(..., user="...")` | **UNSUPPORTED** | Raises TypeError | Kwarg not in Engine |
| **Permission Check**| `Permission.check_permissions(q)`| **SUPPORTED** | Checks read/select |
| **SQL Inspection** | `query.get_sql()` | **SUPPORTED** | Returns SQL string |
| **Debug Mode** | `query.run(debug=True)` | **SUPPORTED** | Logs query & time |
| **Record Locking** | `for_update=True` | **SUPPORTED** | Adds FOR UPDATE |

---

## 4. Frappe Support vs. FlexiRule Relevance Taxonomy

| Capability | Frappe v15 Support | FlexiRule Query Records Relevance | Architectural Classification |
| :--- | :--- | :--- | :--- |
| **Explicit Field Selection** | Supported | **Core** | Frontend config passes native field list |
| **Dotted Link Traversal** | Supported (Select & Filter) | **Core** | Enable link field selection in Query Records |
| **Dotted Child Traversal** | Supported (Select & Filter) | **Core** | Core mechanism for child table filtering |
| **Structured Child Fetching** | Supported (`{"items": [...]}`) | **Core** | Enable nested child table payload retrieval |
| **Distinct Parent Rows** | Supported (`distinct=True`) | **Core** | Prevent duplicate parent records when filtering child tables |
| **Pypika Criterion Filters** | Supported | **Core (Backend)** | Backend handler compiles UI filter trees to Criterion |
| **SQL String Aggregations** | Supported (`count(x) as y`) | **Core / Advanced** | Use for count / aggregate Query Records actions |
| **Pagination (Limit/Offset)** | Supported | **Core** | Expose limit and page offset controls |
| **Permission Enforcement** | Via `Permission.check_permissions` | **Core Security** | Invoke `Permission.check_permissions` explicitly |
| **Pypika Function Objects** | Supported (`Now()`, `Count()`) | **Advanced / Backend** | Standardize function resolution in backend |
| **Record Locking (`FOR UPDATE`)**| Supported | **Advanced / Optional** | Reserve for transactional process execution |
| **Dotted Link Order By** | Unsupported | **Not Exposed** | Direct dotted order_by must be sanitized or mapped |
| **Dict Aggregation Syntax** | Unsupported | **Not Exposed** | Do NOT use dict syntax for functions/aggregates |

---

## 5. Documentation Mismatches Identified

1. **Dict-Based Aggregation Syntax Mismatch:**
   * *Documentation hypothesis:* `fields=[{"COUNT": "name", "as": "total"}]`
   * *Installed Frappe v15 reality:* **REJECTED.** `Engine.parse_fields` interprets any dictionary in `fields` as a child table query (`ChildQuery`). Passing `{"COUNT": "name"}` causes `ChildQuery` to look up table field `"COUNT"`, raising `AttributeError: 'NoneType' object has no attribute 'fieldtype'`.
   * *Correct Working Approach:* Use string function expressions (e.g. `fields=["count(name) as total"]`) or Pypika `Count()` objects.

2. **Dict-Based Scalar Function Syntax Mismatch:**
   * *Documentation hypothesis:* `fields=[{"IFNULL": ["field", "'default'"], "as": "alias"}]`
   * *Installed Frappe v15 reality:* **REJECTED** with `AttributeError` for the same reason.

3. **Infix String `"or"` in List Filters:**
   * *Documentation hypothesis:* `filters=[["status", "=", "Open"], "or", ["status", "=", "Pending"]]`
   * *Installed Frappe v15 reality:* **BROKEN.** `Engine.apply_filters` loops through list elements and converts string `"or"` into `{"name": "or"}`, resulting in `WHERE name = 'or'`, returning 0 records.
   * *Correct Working Approach:* Compile OR filter conditions into Pypika `Criterion` objects before passing to `get_query(filters=...)`.

4. **`ignore_permissions` & `user` Kwargs on `get_query()`:**
   * *Documentation hypothesis:* `frappe.qb.get_query("DocType", ignore_permissions=True, user="...")`
   * *Installed Frappe v15 reality:* **REJECTED** with `TypeError: Engine.get_query() got an unexpected keyword argument`.
   * *Correct Working Approach:* Call `frappe.database.query.Permission.check_permissions(query, user=...)` explicitly when user permissions need to be validated.

---

## 6. Summary & Potential Query Records Implications

### Key Evidence-Based Takeaways
1. **Frontend-to-Backend Filter Contract:** Frontend configurations specifying complex logical groups (AND/OR, nested brackets) must be compiled by FlexiRule into native Pypika `Criterion` objects or normalized tuples, because Frappe's `get_query` filter list parser cannot handle infix `"or"` strings.
2. **Child Table Fetching & Deduplication:** `frappe.qb.get_query` natively supports both flat child joins (`fields=["items.item_code"]`) and structured nested child fetching (`fields=["name", {"items": ["item_code", "qty"]}]`). `distinct=True` must be set when querying parent records filtered by child tables to prevent row duplication.
3. **Aggregation & Function Execution:** FlexiRule should serialize aggregation and field transformations using SQL string expressions (`"count(name) as total"`) or backend Pypika function objects (`Count()`, `Sum()`), avoiding the broken dict syntax.
4. **Permission Architecture:** FlexiRule's security checks must explicitly call `Permission.check_permissions(query, user=user)` rather than relying on non-existent `ignore_permissions` kwargs on `get_query()`.
5. **Executable Verification:** The test module `flexirule/ruleflow/tests/test_frappe_qb_capabilities.py` serves as a permanent, repeatable benchmark suite to verify Frappe query builder behavior across future framework updates.
