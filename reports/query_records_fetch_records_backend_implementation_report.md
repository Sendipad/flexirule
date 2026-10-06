# Query Records — "Fetch Records" Backend Operation Implementation Report

## Overview

This report documents the backend implementation of the **Fetch Records** operation under FlexiRule's existing **Query Records** Action Type (`action_type: "Query Records"`, `operation: "Fetch Records"`). The new operation is powered natively by Frappe Framework's modern `frappe.qb.get_query` API.

---

## 1. Existing Query Records Architecture Discovered

FlexiRule's `QueryRecordsHandler` (`flexirule/ruleflow/core/action_handlers/query_records.py`) serves as the action handler for database queries across rule flows. Prior to this task, it supported the following operations:

- **Query List**: Uses `frappe.get_list()` returning a list of dicts.
- **Query Doc**: Uses `frappe.get_doc()` returning a single document dict.
- **Exist Record**: Uses `frappe.db.exists()` returning boolean.
- **Query Report**: Uses `frappe.desk.query_report.run()` returning report dataset.
- **Aggregations** (`Count`, `Sum`, `Average`, `Min`, `Max`, `Group By`): Metrics calculations via `frappe.get_list()`.

The architecture enforces contract declarations per operation via `OperationContract` objects registered in `get_operation_contracts()`. All existing modes remain behaviorally unchanged and intact alongside `Fetch Records`.

---

## 2. New "Fetch Records" Backend Contract

The contract for `fetch_records` is declared in `QueryRecordsHandler.get_operation_contracts()`:

```python
"Fetch Records": OperationContract(
    operation="Fetch Records",
    rule_overrides=standard_trigger_overrides(
        trigger_events=BROAD_TRIGGER_EVENTS,
        trigger_types=STANDARD_TRIGGER_TYPES,
    ),
    action_overrides=[
        {"fieldname": "action_type", "default": "Query Records"},
        {"fieldname": "operation", "default": "Fetch Records"},
        reference_doctype_override(),
        {"fieldname": "reference_docname", "hidden": 1, "reqd": 0},
        config_depends_on_doctype(description="Frappe Query Builder configuration"),
        {
            "fieldname": "mutation_mode",
            "options": [
                "Set Context Variable",
                "Append to Context Variable",
                "Update Context Variable",
            ],
            "reqd": 1,
        },
        {"fieldname": "return_type", "default": "List of Records", "read_only": 1},
        {
            "fieldname": "timeout",
            "hidden": "eval:doc.parent.execution_mode!=='Asynchronous'",
            "description": "Only available for async rules",
        },
        {
            "fieldname": "description",
            "description": "Queries records using Frappe Query Builder (frappe.qb.get_query)",
        },
    ],
    validation={"backend": "validate_fetch_records"},
)
```

### JSON Schema / Payload Structure

The configuration payload stored in `action.config` accepts:

| Property                             | Type                                 | Required / Default                           | Description                                                                                                                   |
| ------------------------------------ | ------------------------------------ | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `doctype_name` / `reference_doctype` | `str`                                | Required                                     | Target DocType to query                                                                                                       |
| `fields`                             | `list[str]` or `str` or `list[dict]` | Optional (Default: `None` -> selects `name`) | Field paths, aliases (`"email as user_email"`), wildcard `*`, or structured child table fields (`[{"items": ["item_code"]}]`) |
| `filters`                            | `dict` or `list`                     | Optional                                     | Dictionary filters, tuple lists, or recursive AND/OR logical filter trees                                                     |
| `order_by`                           | `str`                                | Optional                                     | Sort ordering (e.g., `"creation desc"`, `"customer asc, grand_total desc"`)                                                   |
| `group_by`                           | `str`                                | Optional                                     | Grouping field(s) (e.g., `"customer"`)                                                                                        |
| `limit`                              | `int` or `str`                       | Optional                                     | Page length                                                                                                                   |
| `offset`                             | `int` or `str`                       | Optional                                     | Record offset for pagination                                                                                                  |
| `distinct`                           | `bool`                               | Optional (Default: `False`)                  | Force distinct selection when querying child tables/joins                                                                     |

---

## 3. Handler Execution Flow

The runtime execution flow inside `QueryRecordsHandler._fetch_records`:

1. **Permission Check**: Checks permissions via `can_ignore_permissions(action, context, throw=True)`. If `ignore_permissions` is `False`, enforces read permission via `frappe.has_permission(reference_doctype, "read", throw=True)`.
2. **Selected Fields**: Parses comma-separated field strings or passes structured field arrays.
3. **Dynamic Value Resolution**:
    - Resolves filter values, order_by, group_by, limit, and offset using `_resolve_filters_with_context` and `_resolve_value_expression_with_context`.
4. **Filter Compilation**:
    - Converts filter trees (including nested AND/OR logic, dicts, tuple lists, and dotted child/link fields) into Pypika / Frappe `Criterion` objects using `_compile_filter_tree`.
5. **Query Builder Construction & Execution**:
    - Invokes `query = frappe.qb.get_query(...)` with target table, fields, filters, order_by, group_by, limit, offset, and distinct.
    - Executes `return query.run(as_dict=True)`.

---

## 4. Permission Behavior & Security Architecture

`Fetch Records` strictly adheres to FlexiRule's security model:

- In FlexiRule, `ignore_permissions` is derived explicitly using `can_ignore_permissions(action, context, throw=True)` (requiring System Manager authorization and mandatory `permission_audit_reason`).
- Frappe Framework's `Engine.get_query` builds raw QueryBuilder objects without taking `ignore_permissions` as a keyword argument. Therefore, permission enforcement is strictly performed prior to query construction:
    - When `ignore_permissions` is `False`, `_fetch_records` explicitly invokes `frappe.has_permission(reference_doctype, "read", throw=True)`, throwing `frappe.PermissionError` if the executing user is unauthorized.
    - When `ignore_permissions` is `True`, permission enforcement is bypassed securely in accordance with FlexiRule audit logging rules.

---

## 5. Dynamic Value Handling

Dynamic variables and expressions (e.g., `{vars.target_id}`, `{doc.status}`, or resolver payloads `{"mode": "variable", "value": "vars.x"}`) are processed through FlexiRule's standard resolution engine before query execution:

- Filters, `order_by`, `group_by`, `limit`, and `offset` support dynamic context values.
- Field names and structural query syntax remain validated string references and are not interpolated as arbitrary SQL expressions.

---

## 6. Supported QB Capabilities

The backend contract safely supports the full spectrum of `frappe.qb.get_query` capabilities:

- **Field Selection & Aliases**: String arrays, comma-delimited strings, wildcard `*`, field aliases (`"email as user_email"`).
- **Nested AND/OR Logical Trees**: Clean compilation of recursive AND/OR filter structures.
- **Operators**: `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `not like`, `in`, `not in`, `is`, `between`.
- **Pagination & Ordering**: `limit`, `offset`, `order_by`, `group_by`, `distinct`.
- **Structured Child Records**: Nested child table selection (e.g., `[{"items": ["item_code", "qty"]}]`).

---

## 7. Child & Link Field Behavior

Relationship field traversals (e.g., `customer.customer_name` for Link fields, `items.item_code` for Child Tables) are handled cleanly:

- Dotted field paths in filters and field selections are converted to native child/link DocType references via `_resolve_filter_doctype_and_field` and Frappe QB's implicit joins.
- `_doctype_has_field` recursively inspects both Link fields and Child Table fields on target DocTypes during validation.

---

## 8. Result Structure

In accordance with Query Records conventions:

- `_fetch_records` returns a `list[dict]` directly:
    ```json
    [
	{ "name": "TASK-0001", "description": "Review PR", "status": "Open" },
	{ "name": "TASK-0002", "description": "Run tests", "status": "Closed" }
    ]
    ```
- No extra wrapping object or separate count query is added.

---

## 9. Validation Rules

Validation is handled by `validate_fetch_records(action, config)` and registered in `OperationContract`:

1. **Reference DocType**: Must be specified and exist in `frappe.db.exists("DocType", ...)` / `frappe.get_meta(...)`.
2. **Field References**: Plain field references in `fields`, `order_by`, and `group_by` are checked against DocType metadata (including dotted Link and Child Table fields).
3. **Filter Fields**: Validated against target or linked DocTypes.
4. **Pagination**: `limit` and `offset` must be non-negative integers or dynamic expression strings.
5. **Distinct**: Must be a boolean value.

---

## 10. Tests Added

Comprehensive backend test coverage is implemented in `flexirule/ruleflow/tests/test_fetch_records.py`:

- `test_basic_fetch_records_default_fields`: Basic record retrieval and default field selection.
- `test_explicit_fields_and_aliases`: Field selection and column aliasing.
- `test_filter_operators`: Tested `=`, `!=`, `like`, `in`, `not in`, `between`, `is`.
- `test_nested_logical_filters_and_or`: Recursive AND/OR filter trees.
- `test_child_table_field_query_and_distinct`: Dotted child table queries and `distinct=True`.
- `test_ordering_limit_and_offset`: Ordering and pagination.
- `test_dynamic_values_resolution`: Resolving `{vars.param}` dynamic filter values.
- `test_permissions_behavior`: Enforces `frappe.PermissionError` for Guest users when `ignore_permissions=False` and allows System Manager when `ignore_permissions=True`.
- `test_validation_rules`: Rejection of invalid DocTypes, missing fields, and negative pagination values.

All 9 new tests and the full FlexiRule test suite (483 tests) pass with 100% success.

---

## 11. Limitations & Intentionally Deferred Capabilities

- **Raw SQL Injection**: Raw SQL string interpolation and arbitrary Pypika object passing from UI are explicitly prohibited to prevent security escapes.
- **Frontend UI**: Frontend components (`QueryRecordsConfig.vue`, etc.) were explicitly out of scope for this task and will be updated in the subsequent task.

---

## 12. Exact Frontend Work for the Next Task

The upcoming frontend task should build upon this finalized backend contract:

1. **Operation Selector**: Add `"Fetch Records"` as an option under `QueryRecordsConfig.vue`.
2. **Field Selection Control**: Bind `config.fields` to multi-select field inputs (supporting dotted Link/Child Table fields and aliases).
3. **Filter Builder**: Expose standard dictionary/tuple filters and nested AND/OR logical filter trees (serializing to `config.filters`).
4. **Ordering & Pagination UI**: Provide inputs for `order_by`, `limit`, `offset`, and `distinct` toggle.
5. **Result Mutation**: Bind output to standard mutation modes (`Set Context Variable`, `Update Context Variable`, `Append to Context Variable`).
