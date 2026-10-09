# Frappe Query Builder (`frappe.qb.get_query`) Evidence-Based Audit & Capabilities Report

## Executive Summary
This report presents the evidence-backed findings from a source-code analysis and empirical audit of Frappe v15's native Query Builder (`frappe.qb.get_query` / `Engine.get_query`) and FlexiRule's **Fetch Records** integration (`QueryRecordsHandler._fetch_records`).

All findings have been verified in the dedicated empirical test suite `flexirule/ruleflow/tests/test_qb_query_limits.py` (18 test cases) and `flexirule/ruleflow/tests/test_fetch_records.py` (11 test cases).

---

## 1. Audit Classification Matrix across 7 Audit Areas

### 1. Permission Enforcement
- **Classification**: **Confirmed**
- **Evidence & Source Locations**:
  - `flexirule/ruleflow/core/permissions.py:can_ignore_permissions`: Enforces `System Manager` role checks when `ignore_permissions=True` is requested. Non-System Managers trigger `frappe.PermissionError`.
  - `flexirule/ruleflow/utils/frappe_query_compat.py:execute_query`: Enforces row-level permission match conditions via `Permission.check_permissions` and `DatabaseQuery.build_match_conditions()` when `ignore_permissions=False`.
- **Test References**:
  - `test_15_permissions_and_security`: Verifies authorized query execution.
  - `test_16_can_ignore_permissions_enforcement`: Asserts that `Guest` or non-System Manager callers attempting `ignore_permissions=True` raise `frappe.PermissionError`.

### 2. Field Path & Relationship Resolution Limits
- **Classification**: **Confirmed**
- **Evidence & Source Locations**:
  - `frappe/database/query.py:DynamicTableField.parse`: Splits field paths on the first dot (`linked_fieldname, fieldname`).
  - **1-Level Link Paths** (`target1_link.region`): **Confirmed Supported**. Generates dynamic `LEFT JOIN tabQB Limit Target Level 1`.
  - **Multi-Level Link Paths** (`target1_link.target2_link.code`): **Confirmed Unsupported (Limit)**. Fails in `DynamicTableField.parse` attempting to resolve field `target2_link.code` on Level 1 table, raising an `AttributeError` or SQL error.
  - **Child Table Fields** (`items.item_code`): **Confirmed Supported**. Generates dynamic `LEFT JOIN tabQB Limit Child`.
  - **Child Table Link Fields** (`items.target1_link.region`): **Confirmed Unsupported (Limit)**. Fails in `DynamicTableField.parse`.
- **Test References**:
  - `test_01_one_level_link_path`, `test_02_multi_level_link_path_limits`, `test_03_child_table_field_path`, `test_04_child_table_link_field_path`, `test_05_parent_field_from_child_context`.

### 3. Operator Semantics & Conversion
- **Classification**: **Confirmed**
- **Evidence & Source Locations**:
  - `frappe/database/operator_map.py:OPERATOR_MAP`: Maps native operators (`=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `not like`, `in`, `not in`, `is`, `between`, `descendants of`, `ancestors of`).
  - `flexirule/ruleflow/core/action_handlers/query_records.py:QueryRecordsHandler._normalize_single_filter_operator`: Converts UI operators (`starts with` -> `like "val%"`, `ends with` -> `like "%val"`, `Between` -> `between`, `Timespan` -> `between [start, end]`).
  - `QueryRecordsHandler._coerce_between_value`: Safely converts comma-separated range strings (`"val1, val2"`) or single strings into `[val1, val2]` tuples before passing to PyPika.
- **Test References**:
  - `test_06_native_comparison_operators`, `test_07_native_like_and_in_operators`, `test_08_native_is_operator_and_null_semantics`, `test_09_native_between_operator`, `test_10_flexirule_ui_operator_normalization`, `test_11_fetch_records_execution_with_normalized_operators`, `test_17_malformed_between_values`.

### 4. Logical Filter Trees & Structure Disambiguation
- **Classification**: **Confirmed**
- **Evidence & Source Locations**:
  - `flexirule/ruleflow/core/action_handlers/query_records.py:_normalize_filters_for_backend`: Disambiguates 3-element filter tuples (`[field, op, val]`) from 3-element logical group nodes (`[node1, "or", node2]`) by asserting `isinstance(item[0], str)` and `item[1].lower() not in ("and", "or")`.
  - `flexirule/ruleflow/utils/frappe_query_compat.py:_compile_logical_filters`: Recursively compiles AND/OR list trees into native PyPika Criteria expressions without dropping conditions.
- **Test References**:
  - `test_14_canonical_filter_tree_adapter_and_execution`, `test_18_multi_depth_nested_logical_trees` (3-level deep nested AND/OR tree assertion).

### 5. Filter Tree Serialization
- **Classification**: **Confirmed**
- **Evidence & Source Locations**:
  - `flexirule/ruleflow/utils/filter_tree_adapter.js`: Preserves empty and single-child group editing nodes during serialization.
  - `QueryRecordsHandler._canonical_filter_tree_to_backend`: Converts persisted `QueryFilterTree` JSON objects (`type: "group|leaf"`) into native backend filter tuples.
- **Test References**:
  - `test_14_canonical_filter_tree_adapter_and_execution`, `test_canonical_filter_tree_is_converted_at_backend_boundary`.

### 6. Security & Parameterization
- **Classification**: **Confirmed**
- **Evidence & Source Locations**:
  - `QueryRecordsHandler._validate_doctype_field_references`: Validates selected fields and filter columns against DocType metadata (`frappe.get_meta`), preventing arbitrary column injection.
  - Parameterized PyPika placeholders and Frappe QB engine prevent raw string SQL interpolation.
- **Test References**:
  - `test_nested_filter_validation`, `test_validation_rules`.

### 7. Test Quality & Isolation
- **Classification**: **Confirmed**
- **Evidence & Source Locations**:
  - Custom test DocTypes (`QB Limit Parent`, `QB Limit Child`, `QB Limit Target Level 1`, `QB Limit Target Level 2`) are isolated in `setUpClass` and explicitly deleted in `tearDownClass`.
  - Test assertions check exact returned record sets, field values, and expected error types.
- **Test References**:
  - `flexirule/ruleflow/tests/test_qb_query_limits.py`.

---

## 2. Capability & Limitation Summary Matrix

| Capability / Path / Operator | Status | Behavior / Limit |
| :--- | :--- | :--- |
| **Direct Field** (`field`) | Supported | Selected on root table |
| **1-Level Link** (`link.field`) | Supported | Auto-creates `LEFT JOIN tabTarget` |
| **Multi-Level Link** (`link1.link2.field`) | Unsupported | Limit in `DynamicTableField.parse` (>1 dot) |
| **Child Table Field** (`child.field`) | Supported | Auto-creates `LEFT JOIN tabChild` |
| **Child Table Link** (`child.link.field`) | Unsupported | Limit in `DynamicTableField.parse` |
| **`starts with` / `ends with`** | Normalized | Converted to `like "val%"` / `like "%val"` |
| **`Between` / `Timespan`** | Normalized | Coerced to `between [start, end]` |
| **Boolean / Check Fields** | Coerced | Native `True`/`False` converted to `1`/`0` |
| **Row-Level Permissions** | Enforced | Filtered via `DatabaseQuery.build_match_conditions()` |

---

## 3. Remaining Release Risks & Recommendations
1. **Multi-Level Link Traversals**: Users selecting multi-level dotted field paths in UI (e.g. `customer.territory.region`) will receive query validation or execution errors because `frappe.qb.get_query` does not support >1 level link joins. **Recommendation**: UI field selection dropdowns should limit navigation depth to 1 link level for Fetch Records actions.
2. **Child Table Link Traversals**: Querying link fields inside child tables (e.g. `items.item_code.item_group`) is unsupported natively. **Recommendation**: Use direct child table field selection or multi-action sub-queries.
