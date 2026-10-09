# Frappe Query Builder (`frappe.qb.get_query`) Evidence-Based Audit & Capabilities Report

## Executive Summary
This report presents the evidence-backed findings from a source-code analysis and empirical audit of Frappe v15's native Query Builder (`frappe.qb.get_query` / `Engine.get_query`) and FlexiRule's **Fetch Records** integration (`QueryRecordsHandler._fetch_records`).

The audit separates native Frappe v15 capabilities from FlexiRule's normalization layer, documenting exact failure stages, exception classes, and verification results across 31 backend unit tests in 5 dedicated, safe test modules:
1. `test_qb_field_path_capabilities.py` (5 tests)
2. `test_qb_operator_capabilities.py` (6 tests)
3. `test_qb_fieldtype_value_matrix.py` (3 tests)
4. `test_fetch_records_normalization.py` (4 tests)
5. `test_fetch_records_filter_tree_integration.py` (2 tests)
6. `test_fetch_records.py` (11 tests)

---

## 1. Test Safety & Isolation Architecture
To prevent pre-existing data or DocType deletion on developer or shared Frappe sites:
- **Tracked Resource Creation**: Each test module maintains `_created_doctypes = []` flags. `tearDownClass` only deletes DocTypes explicitly created by that test suite.
- **Fixture Isolation**: Uniquely named test DocTypes (`QB Path Parent`, `QB Op Parent`, `QB Matrix Parent`, `QB Tree Parent`) prevent namespace collisions.

---

## 2. Audit Findings by Category

### A. Field Path & Relationship Resolution Limits
- **1-Level Link Path** (`target1_link.region`):
  - **Native Frappe Status**: **Supported**.
  - **Behavior**: `DynamicTableField.parse` constructs a dynamic `LEFT JOIN tabTarget`.
- **Multi-Level Link Chain (2+ Levels)** (`target1_link.target2_link.code`):
  - **Native Frappe Status**: **Unsupported (Limit)**.
  - **Failure Stage & Exception**: Fails in AST parsing inside `frappe/database/query.py:DynamicTableField.parse` line 404 (`linked_fieldname, fieldname = field.split(".")`), raising `ValueError: too many values to unpack (expected 2)`.
- **Child Table Field** (`items.item_code`):
  - **Native Frappe Status**: **Supported**.
  - **Behavior**: `DynamicTableField.parse` constructs `LEFT JOIN tabChild` on `parent = root.name` & `parenttype = root.doctype`.
- **Child Table Link Field** (`items.target1_link.region`):
  - **Native Frappe Status**: **Unsupported (Limit)**.
  - **Failure Stage & Exception**: Fails during AST parsing in `DynamicTableField.parse`, raising `ValueError: too many values to unpack (expected 2)`.

### B. Operator Semantics & Conversion
- **Native Operators** (`=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `not like`, `in`, `not in`, `is`, `between`):
  - **Native Frappe Status**: **Supported**.
  - **Empty Sequences in `in`**: Converted by `Engine._apply_filter` to `("",)` to avoid SQL syntax errors.
  - **`is` Operator**: `is set` evaluates to `IS NOT NULL AND field != ''`. `is not set` evaluates to `IS NULL OR field = ''`.
  - **Unsupported Operators**: Passing an unmapped operator string (e.g. `invalid_op`) raises `KeyError` during `OPERATOR_MAP` lookup in `frappe/database/query.py`.
- **FlexiRule UI Operators** (`starts with`, `ends with`, `Between`, `Timespan`):
  - **FlexiRule Normalization**: `QueryRecordsHandler._normalize_single_filter_operator` converts `starts with` -> `like "val%"`, `ends with` -> `like "%val"`, `Between` -> `between`, and `Timespan` -> `between [start, end]`.
  - **`Between` Value Shapes**: `QueryRecordsHandler._coerce_between_value` normalizes list/tuple `[start, end]`, comma strings `"val1, val2"`, and single strings `"val1"` (coerced as single-day range `("val1", "val1")`).

### C. Logical Filter Trees & Structure Disambiguation
- **Nested AND/OR Trees**:
  - **FlexiRule Normalization**: `QueryRecordsHandler._normalize_filters_for_backend` inspects 3-element list items `[a, b, c]` and confirms `isinstance(a, str)` and `b.lower() not in ("and", "or")` before treating as a filter leaf, preventing 3-element logical group nodes `[node1, "or", node2]` from being incorrectly flattened into stringified leaves.
  - **Execution**: `frappe_query_compat.py:_compile_logical_filters` compiles nested AND/OR trees (including 3-level deep structures `A AND (B OR (C AND D))`) into PyPika Criteria.

### D. Permission Enforcement
- **Permission Checking**: `can_ignore_permissions(action, context, throw=True)` verifies `System Manager` roles before allowing `ignore_permissions=True`. Calling with non-System Manager raises `frappe.PermissionError`.
- **Row-Level Filters**: When `ignore_permissions=False`, `frappe_query_compat.py:execute_query` compiles match conditions via `DatabaseQuery.build_match_conditions()`.

---

## 3. Capability Matrix

| Path / Operator | Native Frappe | FlexiRule Normalization | Failure Stage / Notes |
| :--- | :--- | :--- | :--- |
| `field` | **Supported** | Direct | Selected on root table |
| `link1.field` | **Supported** | Direct | Dynamic `LEFT JOIN` on Level 1 table |
| `link1.link2.field` | **Unsupported** | None | `ValueError: too many values to unpack (expected 2)` in `DynamicTableField.parse` |
| `items.item_code` | **Supported** | Direct | Dynamic `LEFT JOIN` on child table |
| `items.link1.field` | **Unsupported** | None | `ValueError: too many values to unpack (expected 2)` in `DynamicTableField.parse` |
| `starts with` / `ends with` | Unsupported | Normalized | Converted to `like "val%"` / `like "%val"` |
| `Between` / `Timespan` | Unsupported | Normalized | Coerced to `between [start, end]` |
| `True` / `False` | **Supported** | Direct | Coerced by `_apply_filter` to `1` / `0` |

---

## 4. Remaining Release Risks & Recommendations
1. **Dotted Path UI Navigation Depth**: Because `frappe.qb.get_query` fails on >1 level dotted paths, the UI field selector for Fetch Records should restrict navigation stack traversals to 1 link level or child table level.
2. **Child Table Link Traversals**: Traversals through child tables into link fields (e.g. `items.target_link.region`) are natively unsupported by `frappe.qb.get_query`. Users requiring child link fields should use direct child table queries or multi-action sub-queries.
