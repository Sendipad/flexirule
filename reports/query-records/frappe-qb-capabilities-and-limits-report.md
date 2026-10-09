# Frappe Query Builder (`frappe.qb.get_query`) Evidence-Based Audit & Capabilities Report

## Executive Summary
This report presents the evidence-backed findings from a source-code analysis and empirical audit of Frappe v15's native Query Builder (`frappe.qb.get_query` / `Engine.get_query`) and FlexiRule's **Fetch Records** integration (`QueryRecordsHandler._fetch_records`).

All findings have been empirically tested and asserted across 36 backend unit tests in 6 dedicated, safe test modules:
1. `test_qb_field_path_capabilities.py` (5 tests)
2. `test_qb_operator_capabilities.py` (6 tests)
3. `test_qb_tree_capabilities.py` (5 tests)
4. `test_qb_fieldtype_value_matrix.py` (3 tests)
5. `test_fetch_records_normalization.py` (4 tests)
6. `test_fetch_records_filter_tree_integration.py` (2 tests)
7. `test_fetch_records.py` (11 tests)

---

## 1. Test Safety & Resource Isolation Architecture
To ensure running tests never deletes pre-existing data or DocTypes on developer or shared Frappe sites:
- **Tracked Resource Creation**: Each test module maintains `_created_doctypes: ClassVar[list[str]] = []`. `tearDownClass` strictly deletes ONLY DocTypes explicitly created during that test run.
- **Unique Namespace Isolation**: Uniquely named test DocTypes (`QB Path Parent`, `QB Op Parent`, `QB Tree Node`, `QB Matrix Parent`, `QB Tree Parent`) prevent namespace collisions.

---

## 2. Comprehensive Capability & Operator Audit

### A. Field Path & Relationship Resolution Limits
- **1-Level Link Path** (`target1_link.region`): **Confirmed Supported**. `DynamicTableField.parse` constructs `LEFT JOIN tabQB Path Target 1`.
- **Multi-Level Link Chain (2+ Levels)** (`target1_link.target2_link.code`): **Confirmed Unsupported (Limit)**. Fails during AST parsing inside `frappe/database/query.py:DynamicTableField.parse` line 404 (`linked_fieldname, fieldname = field.split(".")`), raising `ValueError: too many values to unpack (expected 2)`.
- **Child Table Field** (`items.item_code`): **Confirmed Supported**. `DynamicTableField.parse` constructs `LEFT JOIN tabQB Path Child`.
- **Child Table Link Field** (`items.target1_link.region`): **Confirmed Unsupported (Limit)**. Fails during AST parsing in `DynamicTableField.parse`, raising `ValueError: too many values to unpack (expected 2)`.

### B. Complete Native Operator Matrix
- **Comparison Operators** (`=`, `!=`, `>`, `>=`, `<`, `<=`):
  - **Native Frappe Status**: **Supported**. Tested against integers, floats, currency, and data fields.
- **Pattern Operators** (`like`, `not like`):
  - **Native Frappe Status**: **Supported**. Tested with `%` (multi-char) and `_` (single-char) wildcards.
- **Set Membership** (`in`, `not in`):
  - **Native Frappe Status**: **Supported**. Empty sequences `[]` are safely converted by `Engine._apply_filter` to `("",)`, preventing SQL syntax errors.
- **Null and Set Semantics** (`is set`, `is not set`, `= None`):
  - **Native Frappe Status**: **Supported**. `is set` matches non-null and non-empty values (`IS NOT NULL AND field != ''`). `is not set` matches BOTH `SQL NULL` and empty strings `""` (`IS NULL OR field = ''`).
- **Tree DocType Hierarchy Operators** (`descendants of`, `descendants of (inclusive)`, `ancestors of`, `not descendants of`, `not ancestors of`):
  - **Native Frappe Status**: **Supported**. Executed via `frappe/database/query.py:get_nested_set_hierarchy_result` against Tree DocType `lft` and `rgt` columns. `descendants of` returns all recursive descendants excluding the queried node. `descendants of (inclusive)` includes the queried node. Non-existent node names evaluate safely to empty result set `0` without raising SQL errors.
- **Range Operator** (`between`):
  - **Native Frappe Status**: **Supported**. Tested with numeric ranges `[10, 20]` and date ranges.

### C. FlexiRule Normalization & Value Coercion
- **UI Operators** (`starts with`, `ends with`, `Between`, `Timespan`):
  - `QueryRecordsHandler._normalize_single_filter_operator` converts `starts with` -> `like "val%"`, `ends with` -> `like "%val"`, `Between` -> `between`, and `Timespan` -> `between [start, end]`.
- **`Between` Value Shapes**:
  - `QueryRecordsHandler._coerce_between_value` converts lists/tuples `[start, end]`, comma strings `"val1, val2"`, and single strings `"val1"` (coerced as single-day range `("val1", "val1")`).
- **Logical Group Disambiguation**:
  - `QueryRecordsHandler._normalize_filters_for_backend` asserts `isinstance(item[0], str)` and `item[1].lower() not in ("and", "or")` before treating a 3-element list `[a, b, c]` as a filter leaf, preserving nested AND/OR logical trees up to 3+ depths (`A AND (B OR (C AND D))`).

---

## 3. Full Capability Matrix

| Path / Operator | Native Frappe | FlexiRule Normalization | Failure Stage / Notes |
| :--- | :--- | :--- | :--- |
| `field` | **Supported** | Direct | Selected on root table |
| `link1.field` | **Supported** | Direct | Dynamic `LEFT JOIN` on Level 1 table |
| `link1.link2.field` | **Unsupported** | None | `ValueError: too many values to unpack (expected 2)` in `DynamicTableField.parse` |
| `items.item_code` | **Supported** | Direct | Dynamic `LEFT JOIN` on child table |
| `items.link1.field` | **Unsupported** | None | `ValueError: too many values to unpack (expected 2)` in `DynamicTableField.parse` |
| `=`, `!=`, `>`, `>=`, `<`, `<=` | **Supported** | Direct | Executed via PyPika comparison |
| `like`, `not like` | **Supported** | Direct | Executed with `%` and `_` wildcards |
| `in`, `not in` | **Supported** | Direct | Empty list converted to `("",)` |
| `is set`, `is not set` | **Supported** | Direct | Matches NULL and empty string `""` |
| `descendants of` | **Supported** | Direct | Evaluates Tree DocType `lft` and `rgt` |
| `ancestors of` | **Supported** | Direct | Evaluates Tree DocType `lft` and `rgt` |
| `starts with` / `ends with` | Unsupported | Normalized | Converted to `like "val%"` / `like "%val"` |
| `Between` / `Timespan` | Unsupported | Normalized | Coerced to `between [start, end]` |

---

## 4. Remaining Release Risks & Recommendations
1. **Dotted Path UI Depth**: UI ComboBox controls for Fetch Records should constrain dotted field navigation to 1 link level or direct child table level, as >1 level dotted chains trigger `ValueError: too many values to unpack` in `frappe.qb.get_query`.
2. **Child Table Link Fields**: Traversing link fields within child tables (e.g. `items.target_link.region`) is natively unsupported by `frappe.qb.get_query`. Direct child queries or multi-action sub-queries should be recommended for child link references.
