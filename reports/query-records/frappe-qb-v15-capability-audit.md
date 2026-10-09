# Frappe v15 `frappe.qb.get_query` Architectural Capability Audit Report

## Executive Summary

This report separates three evidence categories that must not be conflated:

1. **Native Frappe Query Builder characterization** — observations about the installed Frappe v15 `frappe.qb.get_query()` API and its SQL/runtime behavior. These characterize Frappe, not the correctness of FlexiRule's adapter.
2. **Fetch Records integration evidence** — the latest CI runs for the reviewed head are green: [Server CI run 37973964507](https://github.com/Sendipad/flexirule/actions/runs/37973964507) and [Linters run 37973964439](https://github.com/Sendipad/flexirule/actions/runs/37973964439) completed successfully. The earlier run 37971338723 was red (531 tests, 10 failures, 1 error, 2 skipped) but was superseded by these successful runs. CI success confirms the configured jobs passed; it does not replace targeted assertions for edge cases that the suite may not cover.
3. **Existing-mode legacy regression tests** — `test_query_records_filters.py` also covers legacy tuple/list/dict normalization and established Query Records modes. Keep those compatibility guarantees separate from Fetch Records' new persisted contract.

**Contract discrepancy at the reviewed head:** the intended Fetch Records contract is canonical `group`/`leaf` tree only, but `query_records.py` currently recursively calls `resolve_payload()` on the entire filter object and then invokes `_normalize_filters_for_backend()` for non-canonical list/dict filters. In addition, `test_03_legacy_tuple_and_list_filter_shapes` in `test_fetch_records_filter_tree_integration.py` explicitly expects Fetch Records to accept legacy filters. Both the implementation and that test conflict with the intended strict contract. Legacy normalization should remain available to established modes such as Query List/Get List; Fetch Records should validate and convert only canonical trees.

**Latest CI evidence:** [Server CI run 37973964507](https://github.com/Sendipad/flexirule/actions/runs/37973964507) and [Linters run 37973964439](https://github.com/Sendipad/flexirule/actions/runs/37973964439) both completed successfully for the reviewed head. The earlier failed run 37971338723 is historical and superseded. Keep CI status distinct from the remaining design/test-coverage questions below.

---

## 1. Installed Environment Specifications

* **Frappe Version:** `15.121.1`
* **Frappe Repository Commit:** `8f801ade016078685c3165c96e38f84f249f5309` (branch: `version-15`)
* **Python Version:** `3.12.13`
* **Database Engine:** `MariaDB`
* **Database Version:** `10.11.14-MariaDB-0ubuntu0.24.04.1`
* **Query Builder Implementation Files:**
  * `frappe/query_builder/utils.py` (Defines `get_query()` entry point, `PseudoColumnMapper`, and patches `run()` / `walk()`)
  * `frappe/database/query.py` (Defines `Engine`, `Permission`, `ChildQuery`, `DynamicTableField`, `parse_fields`, `apply_filters`)
  * `frappe/database/operator_map.py` (Defines operator mappings including `NestedSetHierarchy`, `is`, `between`, `timespan`)
  * `frappe/utils/nestedset.py` (Implements `get_ancestors_of`, `get_descendants_of`, `rebuild_tree` for tree hierarchy evaluation)
  * `frappe/query_builder/builder.py` (Database-specific builder overrides for MariaDB & Postgres)

---

## 2. Detailed Capability Audit Findings by Category

### 2.1 Basic Query & Fields Selection
* **`frappe.qb.get_query("DocType")`**: Generates `SELECT name FROM tabDocType`. Omitting fields defaults selection to `name`.
* **Explicit Fields (`fields=["name", "status"]`)**: Generates `SELECT name, status FROM tabDocType`. Returns list of dictionaries with matching keys.
* **Comma-Separated Fields (`fields="name, status"`)**: Supported. `Engine.parse_fields` splits comma-separated string paths.
* **Wildcard (`fields="*"`)**: Generates `SELECT * FROM tabDocType` selecting all table columns.
* **Aliases (`fields=["name as doc_id"]`)**: Generates `SELECT name doc_id FROM tabDocType`. Returned dictionary keys match the alias name (`doc_id`).

### 2.2 Execution Modes & Iterator Support
* **`query.run(as_dict=True)`**: Returns list of dictionaries.
* **`query.run(as_list=True)`**: Returns tuple/list of row tuples.
* **`query.run(pluck=True)`**: Returns a flat list of scalar values for a single selected column.
* **Iterator Execution (`query.run(as_iterator=True)`)**: **SUPPORTED.** Returns a Python generator object (`<class 'generator'>`).
  * `query.run(as_dict=True, as_iterator=True)` yields row dictionaries item-by-item during iteration.
  * `query.run(as_list=True, as_iterator=True)` yields row lists item-by-item during iteration.
  * Completely consumed during test execution with exact row count and dictionary key validation (`{P1, P2, P3}`).

### 2.3 Filter Syntax, Null/Set Operators & Complex Logical OR/AND
* **Dict Equality (`filters={"status": "Open"}`)**: Generates `WHERE status = 'Open'`.
* **Dict Operator (`filters={"qty": [">", 0]}`)**: Generates `WHERE qty > 0`.
* **List Form (`filters=[["status", "=", "Open"]]`)**: Generates `WHERE status = 'Open'`.
* **Null / Set Operators (`is set` / `is not set`)**:
  * Tested on `nullable_text` field (`P1 = "A"`, `P2 = None`, `P3 = "C"`).
  * `filters=[["nullable_text", "is", "set"]]` generates `WHERE nullable_text != ''` and returns exactly `{P1, P3}`.
  * `filters=[["nullable_text", "is", "not set"]]` generates `WHERE nullable_text IS NULL OR nullable_text = ''` and returns exactly `{P2}`.
* **Infix String `"or"` in List Filters (`filters=[["status", "=", "Open"], "or", ["status", "=", "Pending"]]`)**: **UNSUPPORTED / BROKEN.** `Engine.apply_filters` loops through list elements and converts string `"or"` into `{"name": "or"}`, producing `WHERE name = 'or'`, which yields 0 records.
* **Nested Logical Structures via Pypika `Criterion`**: **SUPPORTED.**
  * `((t.status == "Open") & (t.enabled == 1)) | ((t.status == "Pending") & (t.enabled == 1))` generates `WHERE (status='Open' AND enabled=1) OR (status='Pending' AND enabled=1)` and returns `{P1, P2}`.
  * `(t.status == "Open") & ((t.enabled == 1) | (t.status == "Pending"))` generates `WHERE status='Open' AND (enabled=1 OR status='Pending')` and returns `{P1}`.

### 2.4 Filter Operators & Tree Operators
* **Standard Comparison Operators (`=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `not like`, `in`, `not in`)**: Fully supported and verified against exact record sets.
* **Tree / Nested Set Operators (`descendants of`, `ancestors of`, `not descendants of`, `not ancestors of`)**: **SUPPORTED on `is_tree=1` DocTypes.**
  * `Engine._apply_filter` checks `_operator.casefold() in OPERATOR_MAP["nested_set"]` (`NestedSetHierarchy`), calling `get_nested_set_hierarchy_result(ref_doctype, docname, hierarchy)`.
  * `filters=[["name", "descendants of", root_name]]` on `QB Test Tree` generates `WHERE name IN ('Child A', 'Grandchild A', 'Child B')` and returns all descendant nodes.
  * `filters=[["name", "ancestors of", grandchild_name]]` generates `WHERE name IN ('Child A', 'Root')` and returns ancestor nodes.
  * Applying tree operators to a non-tree DocType or non-existent document node raises a `KeyError` or returns empty node tuples.

### 2.5 Link-Field Traversal & Ordering
* **Selecting Dotted Linked Fields (`fields=["name", "target_link.territory", "category_link.group_code"]`)**: Fully supported. Automatically generates multiple `LEFT JOIN` clauses (`tabQB Test Target`, `tabQB Test Category`).
* **Filtering Dotted Linked Fields (`filters={"target_link.territory": "North"}`)**: Fully supported.
* **Dotted Path `order_by="target_link.territory asc"`**: **UNSUPPORTED in string parser.** `Engine.apply_order_by` splits string by comma and prepends table name without resolving join alias, generating `ORDER BY tabQB Test Parent.target_link.territory ASC`, which raises `pymysql.err.OperationalError: Unknown column`.
* **Pypika Join & Ordering**: **SUPPORTED.** Explicitly joining tables and ordering via `orderby(target_table.territory)` generates `ORDER BY tabQB Test Target.territory` and executes successfully.

### 2.6 Child Table Traversal vs. Structured Child Fetching
* **Flat Child Traversal (`fields=["name", "items.item_code"]`)**: Generates `LEFT JOIN tabQB Test Child ON ...`. Duplicates parent rows in the result set for every matching child record (3 rows for parent `P1` with 3 items).
* **Structured Child Fetching (`fields=["name", {"items": ["item_code", "qty"]}]`)**: **SUPPORTED.** Returns distinct parent row dictionaries (`len = 3`). `Engine` instantiates a `ChildQuery` object for `items`, executes a secondary query against `tabQB Test Child`, and embeds child dict lists directly into each parent dictionary (`row["items"] = [...]`).
* **Distinct Parent Deduplication (`distinct=True`)**:
  * For flat query selecting only parent fields (`fields=["name"]`, `filters={"items.item_code": "ITEM-001"}`), `distinct=True` generates `SELECT DISTINCT name FROM ...` and deduplicates parent rows (`{P1, P2}`).
  * If child fields are in SELECT (`fields=["name", "items.item_code"]`), `distinct=True` cannot deduplicate parent rows because distinct applies to the entire row tuple `(name, item_code)`.

### 2.7 Child DocType as Root Query & `parent_doctype`
* **Direct Child Query (`frappe.qb.get_query("QB Test Child")`)**: Fully supported. Generates `SELECT name, item_code, parent, parenttype, parentfield FROM tabQB Test Child`.
* **Filtering Child DocType by Parent Context**: Fully supported using `filters=[["parent", "=", parent_name], ["parenttype", "=", "QB Test Parent"]]`.
* **`parent_doctype` Argument (`frappe.qb.get_query("QB Test Child", parent_doctype="QB Test Parent")`)**: **UNSUPPORTED on `get_query()`.** Raises `TypeError: Engine.get_query() got an unexpected keyword argument 'parent_doctype'`.
* **Permission Enforcement for Child DocTypes**: `parent_doctype` is an argument for permission checks (`Permission.check_permissions(query, parent_doctype="...")` or `frappe.has_permission("QB Test Child", parent_doctype="...")`), not a query builder parameter.

### 2.8 Aggregation & Scalar Functions
* **Documented Dict Aggregation / Scalar Syntax (`fields=[{"COUNT": "name"}]` / `fields=[{"IFNULL": ...}]`)**: **UNSUPPORTED.** `Engine.parse_fields` interprets dictionary objects in `fields` as child table queries (`ChildQuery`). It looks up table field `"COUNT"`, raising `AttributeError: 'NoneType' object has no attribute 'fieldtype'`.
* **Raw String Functions (`fields=["count(name) as total_count"]`)**: Supported for standard SQL functions.
* **Child Dotted Aggregation String (`fields=["sum(items.qty)"]`)**: **UNSUPPORTED.** `Engine.parse_fields` does not trigger automatic child table JOINs when dotted paths are inside raw function strings, raising `OperationalError: Unknown column 'items.qty'`.
* **Pypika Aggregation & Scalar Objects (`Count()`, `Sum()`, `Avg()`, `Min()`, `Max()`, `Now()`, `Coalesce()`, `Concat()`, `Abs()`, `Extract()`)**:
  * Pypika function objects in `fields` generate valid SQL expressions.
  * Pypika explicit child join (`frappe.qb.from_(parent).left_join(child)...`) calculates child `Sum(child.qty)` accurately (`total_qty = 10.0` for `P1`).
  * `Coalesce(PseudoColumnMapper('\`tabQB Test Parent\`.\`target_link\`'), "'None'")` evaluates NULL values properly. Un-table-qualified string column names in function objects cause `PseudoColumnMapper` to treat them as string literals `'target_link'` due to column name resolution rules.

### 2.9 Record Locking
* **`for_update=True`, `skip_locked=True`, `wait=False`**: **SUPPORTED in transaction.**
  * `for_update=True, skip_locked=True` generates `FOR UPDATE SKIP LOCKED`.
  * `for_update=True, wait=False` generates `FOR UPDATE NOWAIT`.
  * Executed inside active transaction (`frappe.db.begin() ... frappe.db.rollback()`).

### 2.10 Permissions & User Context
* **`ignore_permissions=True` / `user="..."` as `get_query()` kwargs**: **UNSUPPORTED.** Raises `TypeError: Engine.get_query() got an unexpected keyword argument`.
* **Permission Checking**: `frappe.qb.get_query()` is strictly a SQL builder. Permission checking is performed via `frappe.database.query.Permission.check_permissions(query, user=user)`.

---

## 3. Evidence-Hardened Capability Matrix

| Capability | Input / API Form | SQL Generation | Execution | Semantic Verification | Status | Root Cause / Exact Limitation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Basic Query** | `get_query("DocType")` | `SELECT name FROM tab` | Success | Returns default `name` | **SUPPORTED** | None |
| **Explicit Fields** | `fields=["a", "b"]` | `SELECT a, b FROM tab` | Success | Returns dicts with `a`, `b` | **SUPPORTED** | None |
| **Comma Fields** | `fields="a, b"` | `SELECT a, b FROM tab` | Success | Splits string into fields | **SUPPORTED** | None |
| **Wildcard Fields**| `fields="*"` | `SELECT * FROM tab` | Success | Returns all schema columns | **SUPPORTED** | None |
| **Field Aliases** | `fields=["a as foo"]` | `SELECT a foo FROM tab` | Success | Returned dict has key `foo` | **SUPPORTED** | None |
| **`as_dict=True`** | `query.run(as_dict=True)` | Native SQL | Success | Returns list of dicts | **SUPPORTED** | None |
| **`as_list=True`** | `query.run(as_list=True)` | Native SQL | Success | Returns list of tuples | **SUPPORTED** | None |
| **`pluck=True`** | `query.run(pluck=True)` | Native SQL | Success | Returns flat value list | **SUPPORTED** | Requires single field |
| **`as_iterator=True`**| `query.run(as_iterator=True)`| Unbuffered SQL | Success | Returns generator yields | **SUPPORTED** | Python generator object |
| **Dict Filters** | `filters={"a": "b"}` | `WHERE a = 'b'` | Success | Exact record set | **SUPPORTED** | None |
| **Dict Op Filters**| `filters={"a": [">", 0]}`| `WHERE a > 0` | Success | Exact record set | **SUPPORTED** | None |
| **List Filters** | `filters=[["a", "=", "b"]]`| `WHERE a = 'b'` | Success | Exact record set | **SUPPORTED** | None |
| **`is set` / `is not set`**| `filters=[["col", "is", "set"]]`| `WHERE col != ''` / `IS NULL`| Success | `{P1, P3}` / `{P2}` | **SUPPORTED** | Semantic null check verified |
| **Infix String OR** | `filters=[..., "or", ...]`| `WHERE name = 'or'` | Success | Returns 0 records | **BROKEN** | `Engine.apply_filters` converts string `"or"` to `{"name": "or"}` |
| **Pypika OR** | `filters=(t.a==1)\|(t.b==2)`| `WHERE (a=1) OR (b=2)`| Success | Exact record set | **SUPPORTED** | Pypika Criterion |
| **Tree Operators** | `filters=[["a", "descendants of", root]]` | `WHERE name IN (...)` | Success | Descendants/Ancestors | **SUPPORTED** | Requires `is_tree=1` DocType |
| **Link Field Select**| `fields=["link.col"]` | `LEFT JOIN tabTarget` | Success | Joined column value | **SUPPORTED** | Auto LEFT JOIN |
| **Link Field Filter**| `filters={"link.col": "v"}`| `WHERE tabTarget.col = v`| Success | Filtered on joined table | **SUPPORTED** | Auto LEFT JOIN |
| **Link String Order**| `order_by="link.col asc"`| `ORDER BY tabParent.link.col`| OperationalError | Unknown column error | **UNSUPPORTED** | `Engine.apply_order_by` string parser unmapped alias |
| **Pypika Link Order**| `.left_join().orderby()`| `ORDER BY tabTarget.col`| Success | Ordered by joined field | **SUPPORTED** | Pypika explicit join |
| **Child Dotted Select**| `fields=["items.col"]` | `LEFT JOIN tabChild` | Success | Duplicates parent rows | **SUPPORTED** | Relational 1:N join |
| **Child Dotted Filter**| `filters={"items.col": "v"}`| `WHERE tabChild.col = v`| Success | Filters on child field | **SUPPORTED** | Relational 1:N join |
| **Structured Child** | `fields=[{"items": ["a"]}]`| `SELECT parent` (Sub-query) | Success | `row["items"] = [...]` dicts | **SUPPORTED** | `ChildQuery` sub-query per parent |
| **Distinct Parent** | `distinct=True` | `SELECT DISTINCT name` | Success | Deduplicates parent rows | **SUPPORTED** | Only when parent fields selected |
| **Child Root Query** | `get_query("Child DocType")`| `FROM tabChild` | Success | Returns child records | **SUPPORTED** | Includes parent, parenttype, parentfield |
| **`parent_doctype`**| `get_query(..., parent_doctype="...")`| N/A | TypeError | Kwarg rejected | **UNSUPPORTED** | Not in `Engine.get_query` signature |
| **Dict Aggregation**| `fields=[{"COUNT": "a"}]`| N/A | AttributeError | Interp. as child query | **UNSUPPORTED** | Dict in fields reserved for `ChildQuery` |
| **String Function** | `fields=["count(a) as x"]`| `SELECT COUNT(a) x` | Success | Calculated aggregate | **SUPPORTED** | Standard SQL string expression |
| **Pypika Functions**| `fields=[Count(t.a)]` | `SELECT COUNT(a)` | Success | Calculated aggregate | **SUPPORTED** | Pypika function object |
| **Dotted Child Sum** | `fields=["sum(items.qty)"]`| N/A | OperationalError | Unknown column error | **UNSUPPORTED** | `Engine` string parser fails child join for functions |
| **Pypika Child Sum**| `.left_join().select(Sum())`| `SELECT SUM(tabChild.qty)`| Success | Exact child sum | **SUPPORTED** | Pypika explicit join |
| **Pypika Now()** | `fields=[Now()]` | `SELECT NOW()` | Success | `datetime.datetime` | **SUPPORTED** | Pypika function object |
| **Pypika Coalesce** | `fields=[Coalesce(col, v)]`| `SELECT COALESCE(col, v)`| Success | Safe fallback value | **SUPPORTED** | Requires `PseudoColumnMapper` column term |
| **Order By / Group By**| `order_by="..."`, `group_by="..."`| `ORDER BY ... GROUP BY ...`| Success | Ordered & grouped | **SUPPORTED** | Standard fields |
| **Pagination** | `limit=10, offset=10` | `LIMIT 10 OFFSET 10` | Success | Page slice | **SUPPORTED** | None |
| **Record Locking** | `for_update=True, skip_locked=True`| `FOR UPDATE SKIP LOCKED`| Success | Lock acquired | **SUPPORTED** | Requires active transaction |
| **`ignore_permissions`**| `get_query(..., ignore_permissions=True)`| N/A | TypeError | Kwarg rejected | **UNSUPPORTED** | Not in `Engine.get_query` signature |
| **`user` Context** | `get_query(..., user="...")`| N/A | TypeError | Kwarg rejected | **UNSUPPORTED** | Not in `Engine.get_query` signature |
| **Permission Check**| `Permission.check_permissions()`| N/A | Success | Asserts read/select | **SUPPORTED** | Separate permission checker class |

---

## 4. Documentation Mismatches Identified

1. **Dict-Based Aggregation & Scalar Function Syntax Mismatch:**
   * *Documentation hypothesis:* `fields=[{"COUNT": "name", "as": "total"}]` or `fields=[{"IFNULL": ["field", "'val'"]}]`
   * *Installed Frappe v15 reality:* **REJECTED with `AttributeError`.** `Engine.parse_fields` interprets any `dict` element in `fields` as a child table query (`ChildQuery`). Since `"COUNT"` is not a child table field, `field.fieldtype` raises `AttributeError: 'NoneType' object has no attribute 'fieldtype'`.
   * *Correct Working Approach:* Use string function expressions (e.g. `fields=["count(name) as total"]`) or Pypika function objects (`Count()`, `Sum()`, `Now()`).

2. **Infix String `"or"` in List Filters:**
   * *Documentation hypothesis:* `filters=[["status", "=", "Open"], "or", ["status", "=", "Pending"]]`
   * *Installed Frappe v15 reality:* **BROKEN.** `Engine.apply_filters` iterates through list elements and parses string `"or"` as `{"name": "or"}`, resulting in `WHERE name = 'or'`, returning 0 records.
   * *Correct Working Approach:* Compile OR filter conditions into Pypika `Criterion` objects before passing to `get_query(filters=...)`.

3. **`ignore_permissions` & `user` Kwargs on `get_query()`:**
   * *Documentation hypothesis:* `frappe.qb.get_query("DocType", ignore_permissions=True, user="...")`
   * *Installed Frappe v15 reality:* **REJECTED with `TypeError`.** `Engine.get_query()` signature does not accept `ignore_permissions` or `user` kwargs.
   * *Correct Working Approach:* Call `frappe.database.query.Permission.check_permissions(query, user=...)` explicitly.

4. **String-Path `order_by` on Dotted Link Fields:**
   * *Documentation hypothesis:* `order_by="target_link.territory asc"`
   * *Installed Frappe v15 reality:* **REJECTED with `OperationalError`.** `Engine.apply_order_by` splits comma strings and prepends table name without resolving join table aliases.
   * *Correct Working Approach:* Construct explicit Pypika joins (`frappe.qb.from_(parent).left_join(target)...`) and pass `.orderby(target_table.territory)`.

5. **Dotted Child Field Sum in String Expressions:**
   * *Documentation hypothesis:* `fields=["sum(items.qty) as total_qty"]`
   * *Installed Frappe v15 reality:* **REJECTED with `OperationalError`.** `Engine.parse_fields` does not trigger child table joins when dotted paths appear inside function strings.
   * *Correct Working Approach:* Use explicit Pypika child joins with `Sum(child_table.qty)`.

---

## 5. Frappe Capability Findings (Fact-Only)

1. `frappe.qb.get_query()` is a lightweight wrapper that instantiates `frappe.database.query.Engine()` and constructs Pypika query builder objects.
2. `Engine` provides automatic `LEFT JOIN` generation for single-level dotted Link field selections/filters (`target_link.territory`) and dotted Child table selections/filters (`items.item_code`).
3. Dotted string field paths in `order_by` do not resolve join aliases in `Engine.apply_order_by`, raising database `OperationalError`. Explicit Pypika joins resolve this completely.
4. Structured child table retrieval (`fields=["name", {"items": ["item_code", "qty"]}]`) executes separate sub-queries via `ChildQuery` and constructs nested dictionary arrays in parent records without row multiplication.
5. Infix string `"or"` in list filters is broken in `Engine.apply_filters`. Complex AND/OR filter trees must be compiled into Pypika `Criterion` objects.
6. Tree operators (`descendants of`, `ancestors of`) are fully supported by `Engine._apply_filter` via `NestedSetHierarchy` on DocTypes configured with `is_tree=1`.
7. `frappe.qb.get_query()` does not take `ignore_permissions`, `user`, or `parent_doctype` kwargs. Permission enforcement is executed separately via `Permission.check_permissions(query, user=user)`.
8. Iterator execution (`as_iterator=True`) returns a Python generator yielding rows item-by-item for `as_dict=True` and `as_list=True`.

---

## 6. FlexiRule Query Records Architectural Implications

The factual audit findings establish clear contracts for the upcoming FlexiRule Query Records refactor:

1. **Query Field Paths:** Simple parent fields (`status`) and dotted link fields (`customer.customer_group`) can be passed directly as string field paths.
2. **Link Traversal:** Read/select and filter operations on linked DocTypes are natively supported by `frappe.qb.get_query()`.
3. **Child-Table Traversal:** Dotted child fields (`items.item_code`) generate relational 1:N joins in flat queries.
4. **Child DocType as Root Query:** Child DocTypes (`tabSales Order Item`) can be queried directly as root DocTypes. However, linking them to parent context requires filtering on `parent`, `parenttype`, and `parentfield`.
5. **`parent_doctype` Handling:** Do not pass `parent_doctype` as a kwarg to `frappe.qb.get_query()`. Pass `parent_doctype` directly to `Permission.check_permissions` or `frappe.has_permission`.
6. **Filtering:** Standard comparison and pattern operators can be passed as simple list tuples `[field, op, val]`.
7. **Nested AND/OR Compilation:** The FlexiRule Condition/Filter Builder must compile UI filter trees (AND/OR, nested brackets) into native Pypika `Criterion` objects before passing to `get_query(filters=...)`.
8. **Distinct Parent Deduplication:** Query Records actions filtering parent documents via child tables must pass `distinct=True` when selecting parent fields to prevent duplicate parent execution.
9. **Ordering:** Order-by on standard fields can be passed as string paths. Dotted linked field order-by must be compiled into explicit Pypika joins.
10. **Grouping:** Standard `group_by` strings are fully supported.
11. **Aggregation:** Serialize aggregate functions using SQL string expressions (`count(name) as total`) or Pypika function objects (`Count()`, `Sum()`). Do not use dict aggregation syntax.
12. **Structured Child Retrieval:** When Query Records needs to return nested document structures for rule execution context, pass structured dict field specifications (`fields=["name", {"items": ["item_code", "qty"]}]`).
13. **Retrieval Modes:** Support `as_dict=True` for record dicts, `pluck=True` for single-column value lists, and `as_iterator=True` for large batch processing.
14. **Permissions:** Perform permission checks explicitly via `Permission.check_permissions(query, user=rule_user)` in the backend handler.
15. **Pypika Compilation Boundary:** Maintain the explicit architectural boundary:
    `FlexiRule UI Config -> Normalized JSON Specification -> FlexiRule Backend Compiler -> Pypika Criterion / Query -> frappe.qb.get_query() -> MariaDB`.


---

## 7. Source Audit Addendum: Canonical Filter Operators and Timespan (Frappe v15.122.0)

**Source baseline for this addendum:** Frappe tag `v15.122.0`, specifically:
- [`frappe/database/operator_map.py`](https://github.com/frappe/frappe/blob/v15.122.0/frappe/database/operator_map.py)
- [`frappe/database/query.py`](https://github.com/frappe/frappe/blob/v15.122.0/frappe/database/query.py)
- [`frappe/database/utils.py`](https://github.com/frappe/frappe/blob/v15.122.0/frappe/database/utils.py)
- [`frappe/utils/data.py`](https://github.com/frappe/frappe/blob/v15.122.0/frappe/utils/data.py)
- [`frappe/model/db_query.py`](https://github.com/frappe/frappe/blob/v15.122.0/frappe/model/db_query.py)

This addendum is a source-code audit, not a claim that every operator has been empirically exercised against both MariaDB and PostgreSQL. Database portability claims require tests against both configured engines.

### 7.1 What the native Query Builder actually dispatches

`frappe.database.query.Engine._apply_filter()` case-folds the supplied operator and dispatches it through `OPERATOR_MAP`. The native map includes:

| Canonical key / family | Native behavior | FlexiRule recommendation |
| --- | --- | --- |
| `=`, `!=`, `<`, `>`, `<=`, `>=` | Standard comparison operators | Expose these exact lowercase/symbol values; display translated business labels separately |
| `in`, `not in` | Membership; a string value is split on commas by Frappe's wrapper | Expose with a list/multi-select value editor where possible |
| `like`, `not like` | SQL LIKE / NOT LIKE | Expose; document that `%` and `_` are SQL wildcard characters |
| `between` | Inclusive range, represented by a two-value sequence | Expose as `between`; require exactly two values |
| `is` | Frappe-specific set-state check | Expose as `is`, with the value restricted to `set` or `not set`; present labels such as “Is set” and “Is not set” |
| `timespan` | Converts a named relative period to a date range, then applies BETWEEN | Expose as `timespan`; show a dedicated choice control populated from Frappe's supported timespan values |
| `regex` | Delegates to PyPika's regex criterion | Do not expose as a cross-database operator until generated SQL and execution are verified on both MariaDB and PostgreSQL |
| `ancestors of`, `descendants of`, `not ancestors of`, `not descendants of`, `descendants of (inclusive)` | Frappe nested-set hierarchy handling | Expose only for Link fields targeting a Tree DocType; test empty, missing-root, root, and multi-level cases |

The map also contains `=<` and `=>` aliases, but these should **not** be persisted by FlexiRule: use the conventional `<=` and `>=` canonical values. The map's `+`, `-`, `*`, and `/` entries are Python arithmetic functions, not useful general-purpose business filter operators; do not offer them as filter comparisons.

**Important distinction:** a key being present in `OPERATOR_MAP` proves dispatch support in this Frappe implementation. It does not, by itself, prove equivalent SQL behavior on both database engines or that the operator is suitable for every field type.

### 7.2 Timespan values supported by Frappe

`frappe.database.operator_map.func_timespan()` calls `get_timespan_date_range(value)` and passes the returned range to the native `between` implementation. Frappe v15.122.0 recognizes these exact string values:

- **Past periods:** `last 7 days`, `last 14 days`, `last 30 days`, `last 90 days`, `last week`, `last month`, `last quarter`, `last 6 months`, `last year`
- **Relative single days:** `yesterday`, `today`, `tomorrow`
- **Current periods:** `this week`, `this month`, `this quarter`, `this year`
- **Future periods:** `next 7 days`, `next 14 days`, `next 30 days`, `next week`, `next month`, `next quarter`, `next 6 months`, `next year`

The values are case-sensitive strings in the implementation's pattern match, so FlexiRule should submit the exact lowercase value. An unknown value returns no range; it must be rejected by frontend/backend validation rather than silently treated as a valid filter.

For business-user UI, keep the operator value `timespan` separate from the option label. For example, the dropdown may show “Last 30 days”, while the persisted option value must be exactly `last 30 days`. Use Frappe's own `frappe.ui.filter_utils.get_timespan_options()` when available, but normalize and verify its returned option values against the backend-supported set; keep a tested fallback list for contexts where that UI helper is unavailable.

### 7.3 Implementation changes made on this branch

The source audit identified the following mismatches and the current branch has now been updated to address them:

1. **Canonical lowercase operators:** `FilterGroup.vue` now uses `between` and `timespan` as operator values, while labels remain separate presentation text. Existing serialized values are case-normalized when hydrated, so previously stored `Between` / `Timespan` values are upgraded in the UI.
2. **Native timespan behavior:** the frontend now renders a dedicated timespan selector and lowercases the selected option value. The backend no longer converts `timespan` into a FlexiRule-computed `between` range; it passes the native `timespan` operator/value to `frappe.qb.get_query()`. Backend validation checks static values against the supported Frappe timespan list.
3. **Convenience operators:** `starts with` and `ends with` have been removed from the Fetch Records operator selector because they are not native `OPERATOR_MAP` keys. The legacy normalizer retains their conversion to `like` for existing modes; they are not accepted by the canonical Fetch Records operator allowlist.
4. **Tree operators:** the backend allowlist now includes `not descendants of` and `descendants of (inclusive)`, as well as the positive/negative ancestor and descendant operators supported by Frappe v15.122.0. The UI limits these options to Link fields targeting a Tree DocType.
5. **Unsupported aliases removed from canonical validation:** `<>` and `not between` are no longer allowed as Fetch Records canonical operator values. Use `!=` and `between`, respectively.
6. **Field-aware restrictions:** the frontend's invalid-operator map was updated to use the lowercase canonical values, while the call into Frappe's UI helper maps `between` / `timespan` to the helper's expected display spelling only at that UI boundary.

**Not yet proven by this source change alone:** the branch has not been tested here against both MariaDB and PostgreSQL. The source-based operator alignment and validation changes must not be represented as cross-database runtime verification. The `regex` operator remains intentionally unavailable until dialect-specific SQL generation and result semantics are tested on both engines.

### 7.4 Recommended contract

Use one canonical operator value end-to-end for Fetch Records:

- The persisted filter tree, frontend option `value`, backend validation, and native Query Builder input all use the same canonical key: for example, `between`, `timespan`, `not in`, or `descendants of`.
- Human-readable labels are a separate presentation mapping: for example, `between → Between`, `timespan → Within a relative date period`, `is → Is set / Is not set`, `< → Before` for Date fields, and `>= → On or after` for Date fields.
- Operator availability is field-aware. Tree operators are offered only when the selected Link field targets a Tree DocType; `between` and `timespan` are offered only for appropriate Date/Datetime fields (and any other field types explicitly validated by FlexiRule).
- `between` values contain exactly two values. `timespan` values must be a member of the exact supported list above. `is` values must be `set` or `not set`. `in` / `not in` values must be normalized to a predictable list/string representation and covered by tests.
- Keep legacy Query List/Get List normalization separate. This recommendation concerns the new Fetch Records canonical tree contract, not a blanket migration of every legacy mode.

### 7.5 Required evidence before calling the operator contract complete

Add/maintain tests that distinguish:
1. source-derived operator availability from actual execution evidence;
2. canonical tree serialization from native Query Builder behavior;
3. MariaDB results from PostgreSQL results;
4. Tree-DocType-only operators from ordinary DocType behavior;
5. exact timespan values and their range boundaries;
6. legacy mode compatibility from Fetch Records' canonical-only contract.

Do not mark `regex` as cross-database supported until its SQL and record results pass on both engines. Do not report tests as executed unless the relevant Frappe v15.122.0 test environment actually ran them.
