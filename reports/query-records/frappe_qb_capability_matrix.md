# Frappe v15 Query Builder (`frappe.qb.get_query`) Capability Matrix & Source Audit Report

## Executive Summary & Source Environment Identification

This report provides a source-backed technical capability audit of Frappe Framework's native Query Builder (`frappe.qb.get_query()`) for FlexiRule integration. All findings in this matrix are derived directly from source inspection of Frappe Framework at commit `8f801ade016078685c3165c96e38f84f249f5309` (branch `version-15`, version `15.121.1`).

### Installed Environment Specifications

* **Frappe Framework Version:** `15.121.1`
* **Frappe Repository Commit:** `8f801ade016078685c3165c96e38f84f249f5309`
* **Python Runtime:** `Python 3.12.13`
* **Database Engine Support:** `MariaDB 10.11+` & `PostgreSQL 14+`
* **Primary Query Builder Source Files:**
  * `frappe/query_builder/utils.py` (Entry point `frappe.qb.get_query()`, query builder patching, child query execution)
  * `frappe/database/query.py` (`Engine`, `DynamicTableField`, `LinkTableField`, `ChildTableField`, `ChildQuery`, `Permission`)
  * `frappe/database/operator_map.py` (`OPERATOR_MAP`, `NestedSetHierarchy`, `func_timespan`, `func_is`, `like`, `func_in`)
  * `frappe/query_builder/functions.py` (`SqlFunctions`, PyPika function wrappers, `ImportMapper`)

---

## 1. Frappe v15.121.1 Query Builder Capability Matrix

| Feature / Dimension | Support Status | Native / Adapted / Unsupported / Privileged | Source Symbol & Path | Detailed Behavior & Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **Simple Field Selection** | Supported | **Native** | `Engine.parse_fields` (`frappe/database/query.py:284`) | Selects explicit table columns (e.g. `["name", "status"]`). Defaults to `["name"]` if omitted. |
| **Wildcard Selection (`*`)** | Supported | **Native** | `Engine.parse_string_field` (`frappe/database/query.py:279`) | Compiles to `table.star` selecting all table columns. |
| **Field Aliases (`as`)** | Supported | **Native** | `Engine.parse_string_field` (`frappe/database/query.py:282`) | Parses `field as alias` syntax and returns dictionary keys matching the alias string. |
| **1-Hop Link Traversal** | Supported | **Native** | `LinkTableField` (`frappe/database/query.py:421`) | Parses `link_field.field`, resolves linked DocType via metadata, and adds automatic `LEFT JOIN`. |
| **Multi-Hop Link Traversal (`a.b.c`)** | **Unsupported** | **Unsupported** | `DynamicTableField.parse` (`frappe/database/query.py:381`) | Splits on single `.` without recursion (`linked_fieldname, fieldname = field.split(".")`). Raises `ValueError`. |
| **Flat Child Table Fields** | Supported | **Native** | `ChildTableField` (`frappe/database/query.py:397`) | Parses `child_table_field.field`, joins child table on `parent` & `parenttype`, returning flat joined rows. |
| **Nested Parent/Child Result** | Supported | **Native** | `ChildQuery` (`frappe/database/query.py:448`) & `execute_child_queries` (`frappe/query_builder/utils.py:91`) | Dict input `{"items": ["item_code", "qty"]}` executes 2 bulk queries (1 parent + 1 child with `parent IN (...)`). Returns nested arrays. |
| **`frappe.get_docs` API** | **Unsupported** | **Unsupported** | N/A | Symbol `get_docs` does not exist in Frappe v15.121.1. Bulk document retrieval relies on `ChildQuery` batching. |
| **Standard Operators (`=`, `!=`, `<`, `>`, `<=`, `>=`)** | Supported | **Native** | `OPERATOR_MAP` (`frappe/database/operator_map.py:126`) | Maps directly to Python standard library `operator` methods. |
| **Pattern Matching (`like`, `not like`)** | Supported | **Native** | `like`, `not like` (`frappe/database/operator_map.py:14, 38`) | Wraps PyPika `.like()` and `.not_like()`. Requires caller to manage `%` wildcards. |
| **Set Operators (`in`, `not in`)** | Supported | **Native** | `func_in`, `func_not_in` (`frappe/database/operator_map.py:26, 50`) | Splits comma-separated strings automatically or accepts lists/tuples. |
| **Range Filter (`between`)** | Supported | **Native** | `func_between` (`frappe/database/operator_map.py:74`) | Converts `[start, end]` payload into PyPika slice-based `BETWEEN` criterion. |
| **Null/Presence (`is set`, `is not set`)** | Supported | **Native** | `func_is` (`frappe/database/operator_map.py:87`) | `set` checks `key != ""`; `not set` checks `isnull() \| (key == "")`. |
| **Timespan Keywords** | Supported | **Native** | `func_timespan` (`frappe/database/operator_map.py:98`) | Evaluates human keywords (e.g. `last 7 days`, `this month`) via `get_timespan_date_range()`. |
| **Tree DocType Hierarchy Operators** | Supported | **Native** | `NestedSetHierarchy` (`frappe/database/query.py:186`) | `descendants of`, `ancestors of`, etc. look up boundaries via `get_nested_set_hierarchy_result()`. Missing nodes evaluate safely to empty tuple `("",)`. |
| **SQL Aggregate Functions** | Supported | **Native** | `Engine.get_function_object` (`frappe/database/query.py:214`) | Accepts `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` with optional aliases. |
| **Grouping (`GROUP BY`)** | Supported | **Native** | `Engine.get_query` (`frappe/database/query.py:88`) | Appends `.groupby(*group_by)` to query builder object. |
| **Pagination (`LIMIT`, `OFFSET`)** | Supported | **Native** | `Engine.get_query` (`frappe/database/query.py:79, 82`) | Appends `.limit()` and `.offset()` integer bounds. |
| **Deduplication (`DISTINCT`)** | Supported | **Native** | `Engine.get_query` (`frappe/database/query.py:85`) | Appends `.distinct()` to query builder object. |
| **Record Locking (`FOR UPDATE`)** | Supported | **Privileged** | `Engine.get_query` (`frappe/database/query.py:88`) | Supports `for_update`, `skip_locked`, and `nowait`. Requires privileged server execution context. |
| **Permission Enforcement** | Supported | **Native** | `Permission.check_permissions` (`frappe/database/query.py:351`) | Extracts all `tab*` tables from generated SQL and verifies `select` or `read` permission via `frappe.has_permission()`. |

---

## 2. Deep Source Code Verification & Architectural Analysis

### 2.1 Query Builder Entry Point & Execution Pipeline

In Frappe v15.121.1, calling `frappe.qb.get_query(table, fields, filters, ...)` delegates to `Engine().get_query()` (`frappe/database/query.py:31`):

```python
# frappe/query_builder/utils.py:58-61
def get_query(*args, **kwargs) -> QueryBuilder:
    from frappe.database.query import Engine
    return Engine().get_query(*args, **kwargs)
```

`Engine.get_query()` constructs a PyPika `QueryBuilder` instance (either `MariaDB` or `Postgres`), applies field selections (`apply_fields`), filter criteria (`apply_filters`), ordering (`apply_order_by`), limits, offsets, grouping, distinct flags, and row-level locking parameters.

When `query.run()` is invoked, Frappe's patched `execute_query` wrapper (`frappe/query_builder/utils.py:80`) converts the PyPika object into parameterized SQL via `NamedParameterWrapper()`, executes the query via `frappe.db.sql()`, checks table permissions via `Permission.check_permissions()`, and triggers nested child query execution if `_child_queries` are present.

---

### 2.2 Field Selection, Aliases, and Relationship Traversal

Field parsing is governed by `Engine.parse_fields()` (`frappe/database/query.py:284`).

1. **Plain Fields & Aliases:**
   Strings are sanitized and converted to PyPika `Field` objects. Aliases matching `field as alias` format are split into `field` and `alias`, yielding `table[field].as_(alias)` (`frappe/database/query.py:282`).

2. **Relationship Traversal via `DynamicTableField`:**
   Dotted field strings (e.g. `customer.customer_name` or `items.item_code`) are parsed by `DynamicTableField.parse()` (`frappe/database/query.py:381`):
   ```python
   # frappe/database/query.py:381-395
   if "." in field:
       alias = None
       if " as " in field:
           field, alias = field.split(" as ")
       linked_fieldname, fieldname = field.split(".")
       linked_field = frappe.get_meta(doctype).get_field(linked_fieldname)
       linked_doctype = linked_field.options
       if linked_field.fieldtype == "Link":
           return LinkTableField(linked_doctype, fieldname, doctype, linked_fieldname, alias=alias)
       elif linked_field.fieldtype in frappe.model.table_fields:
           return ChildTableField(linked_doctype, fieldname, doctype, alias=alias)
   ```

   * **1-Hop Link Fields (`LinkTableField`):** Joins `tab<LinkedDocType>` on `tab<LinkedDocType>.name == tab<ParentDocType>.<link_fieldname>`.
   * **Child Table Fields (`ChildTableField`):** Joins `tab<ChildDocType>` on `tab<ChildDocType>.parent == tab<ParentDocType>.name AND tab<ChildDocType>.parenttype == <parent_doctype>`.
   * **Multi-Hop Traversal Limitation:** Because `field.split(".")` expects exactly 2 items, multi-hop chains (e.g., `customer.customer_group.name`) raise `ValueError: too many values to unpack (expected 2)`. Multi-hop link traversal is **unsupported natively** by `frappe.qb.get_query()` in Frappe v15.121.1.

---

### 2.3 Structured Nested Parent-Child Document Retrieval (`ChildQuery`)

Frappe v15 `frappe.qb.get_query` natively supports nested document retrieval through dictionary field definitions:

```python
# Passing a dictionary in fields list:
frappe.qb.get_query("Sales Invoice", fields=["name", "customer", {"items": ["item_code", "qty", "rate"]}])
```

#### Backend Execution Mechanics:
1. `Engine.parse_fields()` detects the dictionary `{"items": [...]}` and instantiates `ChildQuery("items", ["item_code", "qty", "rate"], "Sales Invoice")` (`frappe/database/query.py:298`).
2. `apply_fields()` attaches `ChildQuery` objects to `query._child_queries`.
3. During `query.run()`, `execute_child_queries()` (`frappe/query_builder/utils.py:91`) runs:
   - Primary parent query executes first, returning parent dicts with `name`.
   - `parent_names = [d.name for d in result]` is extracted.
   - For each `ChildQuery`, a single batched query is generated:
     ```sql
     SELECT item_code, qty, rate, parent, parentfield
     FROM `tabSales Invoice Item`
     WHERE parenttype = 'Sales Invoice'
       AND parentfield = 'items'
       AND parent IN ('SINV-001', 'SINV-002', ...)
     ORDER BY idx asc
     ```
   - Returned child records are attached directly as list arrays under `row["items"]` for each parent object.

#### Key Architectural Finding:
This **2-query execution pattern** (1 parent query + 1 query per child table) guarantees $O(1)$ query complexity relative to result count, completely avoiding N+1 query performance degradation.

---

### 2.4 Filter Engine & Operator Evaluation

Filter processing is driven by `Engine.apply_filters()` (`frappe/database/query.py:121`) and `OPERATOR_MAP` (`frappe/database/operator_map.py:126`).

1. **Leaf Filter Normalization:**
   Supports list/tuple leaves (`[field, val]`, `[field, op, val]`, `[doctype, field, op, val]`) and dictionary specifications (`{"status": "Active", "grand_total": [">", 1000]}`).

2. **Specialized Operator Semantics:**
   * **`is`:** `is set` evaluates to `field != ""`; `is not set` evaluates to `(field.isnull() | (field == ""))`.
   * **`timespan`:** Delegates to `get_timespan_date_range(value)` (`frappe/model/db_query.py`), resolving keyword tokens (`last 7 days`, `this month`, `next quarter`, etc.) into absolute `[start_date, end_date]` tuples.
   * **Tree DocType Nested Sets:** `descendants of`, `ancestors of`, `not descendants of`, `not ancestors of`, `descendants of (inclusive)` resolve hierarchy boundaries via `get_nested_set_hierarchy_result()`. Non-existent node references safely return `("",)` resulting in zero matches without raising SQL errors.

---

### 2.5 Functions, Aggregations & Grouping

Functions are parsed in `Engine.get_function_object()` (`frappe/database/query.py:214`).

* **Supported Functions:** Allowlisted in `SqlFunctions` (`frappe/query_builder/functions.py:169`): `Count`, `Sum`, `Avg`, `Min`, `Max`, `Abs`, `Locate`, `DayOfYear`, `Extract`, `Timestamp`, `IfNull`.
* **Alias Handling:** Function strings containing ` as ` (e.g. `COUNT(name) as total_count`) automatically set `alias="total_count"`.
* **Grouping (`GROUP BY`):** Passed directly to PyPika `.groupby()`.

---

### 2.6 Security & Permission Enforcement Model

Permission enforcement in `frappe.qb.get_query()` is strictly table-level (`frappe/database/query.py:351`):

```python
# frappe/database/query.py:351-365
class Permission:
    @classmethod
    def check_permissions(cls, query, **kwargs):
        if not isinstance(query, str):
            query = query.get_sql()
        doctype = cls.get_tables_from_query(query)
        for dt in doctype:
            dt = TAB_PATTERN.sub("", dt)
            if not frappe.has_permission(dt, "select", ...) and not frappe.has_permission(dt, "read", ...):
                frappe.throw(_("Insufficient Permission for {0}").format(frappe.bold(dt)))
```

#### Security Boundaries:
1. Every table referenced in the generated SQL string (including joined Link tables and joined Child tables) is extracted and verified against `frappe.has_permission(dt, "select")` or `read`.
2. Failing permission checks raise `frappe.PermissionError` (or `ValidationError`), halting query execution immediately.
3. **Child Table Permissions:** In nested document retrieval (`ChildQuery`), child table queries run through `frappe.qb.get_query()` independently, enforcing permission checks on both parent and child DocTypes.

---

## 3. Downstream Consumer Analysis & Result Contracts

Inspection of FlexiRule's codebase reveals how `Query Records -> Fetch Records` results are stored and consumed downstream:

1. **Storage & Mutation (`RuleEngine.execute_action` & `ContextManager.apply_mutation`):**
   * Fetch Records outputs a list of row dictionaries (`list[dict]`).
   * The result payload is stored into `context.vars[return_variable]` according to `mutation_mode`:
     * `Set Context Variable`: Replaces `context.vars[return_variable] = result`.
     * `Append to Context Variable`: Appends or extends `context.vars[return_variable]`.
     * `Update Context Variable`: Merges dict keys.

2. **Downstream Consumers:**
   * **Collection Resolvers (`family: "collection"`):** Expect `context.vars[var_name]` to be a list of dicts or primitives when evaluating `count`, `sum`, `avg`, `filter`, `pluck`, `find`, `unique`.
   * **Condition Nodes:** Access `vars.var_name` to check record counts or evaluate field values.
   * **Loop Nodes:** Iterate over `vars.var_name`.
   * **Jinja Templates & Script Expressions:** Access `vars.var_name[0].field_name`.

#### Backward Compatibility Finding:
Existing saved Fetch Records node configurations store `{ fields, filters, order_by, group_by, limit, offset, distinct }`. When executed, this payload yields a flat list of dicts (`list[dict]`). Wrapping this configuration into the proposed Canonical Query Schema with a default `result_mode: "flat"` preserves 100% runtime contract parity for all existing downstream consumers without requiring data migration.

---

## 4. Operational Boundaries & Unsupported Features Summary

To prevent exposing features in the UI that the Frappe v15 backend cannot safely execute, the UI and schema must enforce the following hard boundaries:

1. **Multi-Hop Link Paths:** Prohibited. Fields like `customer.customer_group.name` must be disabled in the UI and rejected during backend validation.
2. **Arbitrary SQL/Python Expressions:** Prohibited. Only allowlisted functions (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`) and explicit field paths are permitted.
3. **`frappe.get_docs` Assumptions:** Prohibited. Bulk nested document fetching must use native `ChildQuery` batching (`{"child_table": ["f1", "f2"]}`).
