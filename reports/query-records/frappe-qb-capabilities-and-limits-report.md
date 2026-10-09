# Frappe Query Builder (`frappe.qb.get_query`) Capabilities, Limits, and FlexiRule Integration Findings Report

## Executive Summary
This report presents the empirical findings and architectural analysis from a comprehensive investigation into Frappe v15's native Query Builder (`frappe.qb.get_query` / `Engine.get_query`) and FlexiRule's **Fetch Records** query integration.

The primary goal of this audit was to empirically establish:
1. Field path resolution depth limits across Link and Child Table relationships.
2. Operator support, syntax, and value coercion behavior across Frappe fieldtypes.
3. Fetch Records UI filter tree serialization and normalization down to backend PyPika query filters.
4. Security, permission enforcement, parameterization, and SQL safety.

All findings have been empirically tested and asserted in `flexirule/ruleflow/tests/test_qb_query_limits.py` and `flexirule/ruleflow/tests/test_fetch_records.py`.

---

## 1. Field Path & Relationship Resolution Matrix

`frappe.qb.get_query` relies on `DynamicTableField.parse` (`frappe/database/query.py`) to parse dotted field notation into dynamic SQL joins (`LinkTableField` or `ChildTableField`).

| Path Pattern | Example | Native Support (`frappe.qb.get_query`) | Underlying Implementation & Behavior | Recommendation / Limit |
| :--- | :--- | :--- | :--- | :--- |
| **Direct Field** | `title` | **Supported** | Selected on root table `tabDocType` | Standard usage |
| **1-Level Link Path** | `target1_link.region` | **Supported** | `DynamicTableField.parse` parses `linked_fieldname` and `fieldname`, constructing `LEFT JOIN tabTarget`. | Fully supported natively |
| **Multi-Level Link Chain (2+ Levels)** | `target1_link.target2_link.code` | **UNSUPPORTED** | `DynamicTableField.parse` splits only on the first dot (`linked_fieldname, fieldname`), attempting to resolve field `target2_link.code` on `tabTarget Level 1`, which throws an `AttributeError` or SQL column missing error. | **Limit**: Root queries cannot traverse >1 link level natively. Reject or require explicit join construction. |
| **Child Table Field** | `items.item_code` | **Supported** | `DynamicTableField.parse` identifies child table fieldtype `Table`/`Table MultiSelect`, joining `tabChild` on `parent = root.name` & `parenttype = root.doctype`. | Fully supported natively |
| **Child Table Link Field** | `items.target1_link.region` | **UNSUPPORTED** | `DynamicTableField.parse` fails on nested dotted traversal within child tables. | **Limit**: Field paths traversing through child tables into link targets are unsupported natively. |
| **Parent Field from Child Root** | `parent.title` | **UNSUPPORTED (Raw)** | When querying a child table directly, `parent` is a Data column. Traversal `parent.title` is unsupported unless an explicit join to parent DocType is constructed. | **Limit**: Direct child queries require explicit join to access parent fields. |

---

## 2. Operator & Value Formatting Matrix

Frappe's `Engine._apply_filter` maps string operators to PyPika functions via `OPERATOR_MAP` (`frappe/database/operator_map.py`).

| Operator | Native Support | FlexiRule UI Equivalent | Value Requirements & Coercion | Notes & Limitations |
| :--- | :--- | :--- | :--- | :--- |
| `=` / `!=` | **Supported** | Equals / Not Equals | Scalar primitives (str, int, float, bool) or `None` | `True` / `False` are automatically coerced to `1` / `0` by `_apply_filter`. `None` is converted to `IS NULL`. |
| `>`, `>=`, `<`, `<=` | **Supported** | Greater than, Less than, etc. | Numbers, ISO date strings, or Python `date`/`datetime` | Fully supported. |
| `like` / `not like` | **Supported** | Contains / Not Contains | Pattern string (e.g. `%val%`) | FlexiRule UI maps `starts with` -> `val%` and `ends with` -> `%val`. |
| `in` / `not in` | **Supported** | In / Not In | Sequence (list, tuple) of values | Converts empty sequences `[]` to `("",)` to avoid SQL syntax errors. |
| `is` | **Supported** | Is Set / Is Not Set | `"set"` or `"not set"` | `"set"` compiles to `IS NOT NULL AND field != ''`. `"not set"` compiles to `IS NULL OR field = ''`. |
| `between` | **Supported** | Between / Timespan | Sequence `[start, end]` or `(start, end)` | **Native Limitation**: Native `frappe.qb` passes raw strings directly to PyPika. Comma-separated strings like `"val1,val2"` must be normalized into `[val1, val2]` before passing to `frappe.qb.get_query`. |
| `descendants of` / `ancestors of` | **Supported** | Nested Set Hierarchy | Document Name (str) | Resolves tree hierarchy nodes via `get_nested_set_hierarchy_result`. |

---

## 3. FlexiRule Fetch Records Pipeline & Filter Tree Conversion

### Data Flow Pipeline
1. **UI Layer (`QueryFilterTree.vue` / `TreeBuilder.vue`)**:
   - Persists conditions as recursive tree structures (`{ type: "group", operator: "and|or", children: [...] }`) or flat leaf tuples (`[field, op, val]`).
2. **Adapter Layer (`filter_tree_adapter.js`)**:
   - Serializes UI tree state into standard JSON arrays while preserving single-child groups and empty group nodes for editing context.
3. **Action Handler Normalization (`QueryRecordsHandler._fetch_records` in `query_records.py`)**:
   - Resolves dynamic context variables (`{vars.my_var}`).
   - Converts UI operators (`starts with`, `ends with`, `Between`, `Timespan`) into backend-native PyPika filter syntax (`like`, `between`).
   - Normalizes nested AND/OR tree arrays into backend filter tuples without breaking nested logical groupings.
4. **Compatibility & Permission Layer (`frappe_query_compat.py`)**:
   - Builds native PyPika criteria.
   - Enforces Frappe row-level permission match conditions (`Permission.check_permissions`).
   - Executes query via `frappe.qb.get_query(ref_doctype, **kwargs).run(as_dict=True)`.

---

## 4. Empirical Test Suite Coverage

The dedicated empirical test suite `flexirule/ruleflow/tests/test_qb_query_limits.py` validates the following 15 test cases:

1. `test_01_one_level_link_path`: Asserts 1-level link field selection and filtering (`target1_link.region`).
2. `test_02_multi_level_link_path_limits`: Confirms 2+ level link chain (`target1_link.target2_link.code`) is rejected natively by `frappe.qb.get_query`.
3. `test_03_child_table_field_path`: Asserts child table field resolution (`items.item_code`).
4. `test_04_child_table_link_field_path`: Confirms link paths inside child tables (`items.target1_link.region`) are rejected natively.
5. `test_05_parent_field_from_child_context`: Verifies querying child table directly.
6. `test_06_native_comparison_operators`: Verifies `=`, `!=`, `>`, `<=`.
7. `test_07_native_like_and_in_operators`: Verifies `like`, `not like`, `in`, `not in`.
8. `test_08_native_is_operator_and_null_semantics`: Verifies `is` operator with `set` / `not set` and `None`.
9. `test_09_native_between_operator`: Verifies native `between` operator with sequences and Python `date` objects.
10. `test_10_flexirule_ui_operator_normalization`: Asserts `QueryRecordsHandler._normalize_single_filter_operator` for `starts with`, `ends with`, `Between`, `Timespan`.
11. `test_11_fetch_records_execution_with_normalized_operators`: Verifies end-to-end Fetch Records execution with UI filter normalization.
12. `test_12_check_field_boolean_coercion`: Verifies Check field boolean coercion (`True`/`False` -> `1`/`0`).
13. `test_13_date_and_datetime_coercion`: Verifies Date and Datetime field coercion with ISO strings and Python `date` objects.
14. `test_14_canonical_filter_tree_adapter_and_execution`: Verifies full `QueryFilterTree` serialization and query execution.
15. `test_15_permissions_and_security`: Verifies permission check enforcement in `execute_query`.

---

## 5. Security & Permission Assurance

All `frappe.qb.get_query` executions within FlexiRule strictly adhere to:
- **No Unsafe SQL Interpolation**: Field expressions and parameters are compiled through PyPika AST nodes (`frappe.qb.DocType`) and parameterized SQL placeholders.
- **Permission Compliance**: `can_ignore_permissions(action, context, throw=True)` checks `System Manager` roles before allowing `ignore_permissions=True`. Row-level permission conditions are compiled via `DatabaseQuery.build_match_conditions()` when `ignore_permissions=False`.

---

## 6. Summary of Fixed Integration Defects

During this investigation, two integration edge cases were identified and fixed in `query_records.py`:
1. **Fetch Records Normalization Gate**: Updated `_fetch_records` in `query_records.py` to ensure raw list filter arrays (containing UI operators like `"starts with"` or `"Between"`) are passed through `_normalize_filters_for_backend` before invoking `execute_query`.
2. **Logical Group Disambiguation**: Updated `_normalize_filters_for_backend` to verify that 3-element lists `[a, b, c]` are only treated as filter leaves `[field, op, val]` if `a` is a string field name and `b` is a valid comparison operator (excluding `"and"`/`"or"`), preserving nested AND/OR logical trees.

All tests in `flexirule/ruleflow/tests/test_qb_query_limits.py` and `flexirule/ruleflow/tests/test_fetch_records.py` pass cleanly.
