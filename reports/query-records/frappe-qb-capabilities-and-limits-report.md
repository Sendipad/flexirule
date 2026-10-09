# Frappe Query Builder (`frappe.qb.get_query`) Evidence-Based Audit & Capabilities Report

## Executive Summary
This report presents the evidence-backed findings from a source-code analysis and empirical audit of Frappe v15's native Query Builder (`frappe.qb.get_query` / `Engine.get_query`) and FlexiRule's **Fetch Records** integration (`QueryRecordsHandler._fetch_records`).

All findings have been empirically tested and asserted across 38 backend unit tests in 7 dedicated, safe test modules:
1. `test_qb_field_path_capabilities.py` (5 tests) - Reuses installed `Rule`, `Rule Action`, `Process` DocTypes
2. `test_qb_operator_capabilities.py` (6 tests) - Reuses installed `Rule` DocType
3. `test_qb_tree_capabilities.py` (5 tests) - Retains dedicated `QB Tree Node` DocType (Tree DocType required)
4. `test_qb_fieldtype_value_matrix.py` (3 tests) - Reuses installed `Rule`, `Data Review Task` DocTypes & retains `QB Matrix Temporal` fixture for `Date`/`Currency`
5. `test_fetch_records_normalization.py` (4 tests) - Direct unit tests for `QueryRecordsHandler`
6. `test_fetch_records_filter_tree_integration.py` (2 tests) - Reuses installed `Rule` DocType
7. `test_fetch_records.py` (13 tests) - Reuses installed `Rule` & `Rule Action` DocTypes

---

## 1. Environment & Execution Context
- **Frappe Version**: Frappe v15.121.1 (`apps/frappe`)
- **Database Backend**: MariaDB / MySQL (InnoDB engine on `test_site`)
- **Test Site**: `test_site` (`/home/jules/frappe-bench`)
- **Test Command**: `bench --site test_site run-tests --app flexirule --module flexirule.ruleflow.tests.<module_name>`
- **Total Test Discovery & Results**: 38 total discovered in refactored modules, 38 passed, 0 failed, 0 skipped.

---

## 2. Test Safety, Fixture Reuse & Isolation Architecture
To ensure running tests never delete pre-existing site data, DocTypes, or shared records:
- **Reuse Installed FlexiRule DocTypes**:
  - `Rule`, `Rule Action`, `Process`, and `Data Review Task` are reused across operator capability, filter tree integration, field path capability, and value matrix tests.
  - Reused fields include `rule_name`, `is_active`, `execution_mode`, `priority`, `max_execution_time`, `description`, `resolved_on`, `actions.action_id`, and `process_name.description`.
- **Justified Dedicated Fixtures**:
  - `QB Tree Node`: Retained as a dedicated test DocType because no installed FlexiRule DocType has `is_tree: 1` required to test tree hierarchy operators (`descendants of`, `ancestors of`, etc.).
  - `QB Matrix Temporal`: Retained as a narrowly scoped dedicated test DocType strictly to cover `Date` and `Currency` fieldtypes not present on installed FlexiRule DocTypes.
- **Explicit Ownership Tracking & Safe Teardown**:
  - Unconditional, broad table deletions (`frappe.db.delete("Rule")`, `frappe.db.delete("QB Op Parent")`, etc.) have been completely removed.
  - Each test module assigns unique deterministic identifiers (e.g. `_TEST_QB_...`) and maintains explicit `_created_records: ClassVar[list[tuple[str, str]]]` and `_created_doctypes: ClassVar[list[str]]` tracking.
  - `tearDownClass` deletes ONLY test-owned records and test-created DocTypes, preserving pre-existing records and DocTypes.

---

## 3. Comprehensive Capability & Operator Audit

### A. Comparison Operators (`=`, `!=`, `>`, `>=`, `<`, `<=`)
- **Native Frappe Status**: **Supported (Source-confirmed & Empirically verified)**.
- **Tested Field Types**: Data, Int, Float, Currency, Date, Datetime, Check / Boolean.
- **Operand Representations**:
  - Native Python values (`10`, `3.14159`, `datetime.date(2026, 3, 1)`, `datetime.datetime(...)`, `True`, `False`).
  - Numeric strings (`"42"`, `"50.00"`), ISO date strings (`"2026-03-01"`), and ISO datetime strings (`"2026-03-15 00:00:00"`).
  - Boundary values: Negative integers (`-10`), negative floats (`-0.5`), zero (`0`), and fractional seconds (`2026-03-31 23:59:59.999999`).

### B. Pattern Matching Operators (`like`, `not like`, `starts with`, `ends with`)
- **Wildcard Supply Contract & Double-Wildcarding**:
  1. **Native `like`**: Expects the **caller** to supply wildcards (`%` or `_`). Plain strings without wildcards execute an exact SQL match.
  2. **Native `not like`**: Expects caller-supplied wildcards. Records with `SQL NULL` values in the field are omitted from results due to SQL tri-state logic.
  3. **FlexiRule `starts with` & Characterization Note**:
     - `QueryRecordsHandler._normalize_single_filter_operator` automatically appends `%` to the operand string (`val` -> `val%`).
     - **Observed Behavior**: If an input string is already wildcarded (e.g. `"Test%"`), `starts with` currently produces `"Test%%"`. This observed implementation behavior is documented in characterization test `test_01_ui_operator_normalization` in `test_fetch_records_normalization.py`. Production code remains unchanged in this test refactoring task. If wildcard sanitization/trimming is desired, it should be addressed in a separate focused change.
  4. **FlexiRule `ends with`**: Automatically prepends `%` to the operand string (`val` -> `%val`).

### C. Set Membership (`in` and `not in`)
- **Native Frappe Status**: **Supported (Source-confirmed & Empirically verified)**.
- **List / Sequence Handling**:
  - Lists of native values (`[10, 20]`) and strings.
  - Comma-separated strings (`"CODE_A,CODE_B"`): Natively split by `frappe.database.operator_map.func_in` into `['CODE_A', 'CODE_B']`.
  - Empty lists (`[]`): Natively converted by `Engine._apply_filter` to `("",)`, returning 0 records safely without raising SQL syntax errors.

### D. Range Operators (`between` and `not between`)
- **Native Frappe Status**: **Supported (Source-confirmed & Empirically verified)**.
- **Boundary Inclusivity**: Natively inclusive on both lower and upper bounds (`start <= field <= end`).
- **Date & Datetime Range Semantics**:
  - Tested with ISO Date strings (`["2026-03-01", "2026-03-31"]`) and Datetime strings with microsecond precision (`["2026-03-01 00:00:00", "2026-03-31 23:59:59.999999"]`).
  - FlexiRule `_coerce_between_value` accepts 2-element lists, tuples, comma-separated strings `"start, end"`, and falls back to `(val, val)` for single strings (treating it as a single-day range).

### E. Check / Boolean Coercion
- **Native Frappe Status**: **Supported (Source-confirmed & Empirically verified)**.
- **Boolean Handling**:
  - Python `True` / `False` are converted by `Engine._apply_filter` to integer `1` / `0`.
  - Numeric integers `1` / `0` and numeric strings `'1'` / `'0'` match stored database integer values.
- **FlexiRule Value Coercion (`_extract_filter_value_payload`)**:
  - When wrapped in structured UI dicts with `value_type: "boolean"`, inputs `True`, `1`, `"1"`, `"Yes"`, `"yes"`, `"true"`, `"True"` resolve to `1`.
  - Inputs `False`, `0`, `"0"`, `"No"`, `"no"`, `"false"`, `"False"` resolve to `0`.
  - Plain un-wrapped string variants (e.g. `"true"`) pass through uncoerced to the database.

---

## 4. Complete Coverage Matrix

| Path / Operator | Native Frappe | FlexiRule Normalization | Failure Stage / Notes |
| :--- | :--- | :--- | :--- |
| `field` | **Supported** | Direct | Selected on root table |
| `process_name.description` | **Supported** | Direct | Dynamic `LEFT JOIN` on Level 1 table (`Rule Action` -> `Process`) |
| `link1.link2.field` | **Unsupported** | None | `ValueError: too many values to unpack (expected 2)` in `DynamicTableField.parse` |
| `actions.action_id` | **Supported** | Direct | Dynamic `LEFT JOIN` on child table (`Rule` -> `Rule Action`) |
| `actions.process_name.description` | **Unsupported** | None | `ValueError: too many values to unpack (expected 2)` in `DynamicTableField.parse` |
| `=`, `!=`, `>`, `>=`, `<`, `<=` | **Supported** | Direct | Executed via PyPika comparison |
| `like`, `not like` | **Supported** | Direct | Executed with `%` and `_` wildcards; SQL NULLs excluded under `not like` |
| `in`, `not in` | **Supported** | Direct | Comma-strings split; empty lists converted to `("",)` |
| `is set`, `is not set` | **Supported** | Direct | Matches NULL and empty string `""` |
| `descendants of` | **Supported** | Direct | Evaluates Tree DocType `lft` and `rgt` on `QB Tree Node` |
| `ancestors of` | **Supported** | Direct | Evaluates Tree DocType `lft` and `rgt` on `QB Tree Node` |
| `starts with` / `ends with` | Unsupported | Normalized | Converted to `like "val%"` / `like "%val"` (see double-wildcarding note) |
| `Between` / `Timespan` | Unsupported | Normalized | Coerced to `between [start, end]` |

---

## 5. Summary & Release Recommendations
1. **Fixture Isolation Verification**: All 38 capability and integration tests operate safely without table-wide deletions, cleanly creating and removing test-owned documents and dedicated fixtures.
2. **Dotted Path UI Depth**: UI ComboBox controls for Fetch Records should constrain dotted field navigation to 1 link level or direct child table level, as >1 level dotted chains trigger `ValueError: too many values to unpack` in `frappe.qb.get_query`.
3. **Double Wildcarding**: Users configuring `starts with` in FlexiRule who manually enter a `%` suffix will produce `%%`. A separate focused change may be considered if wildcard sanitization is desired.
4. **Child Table Link Fields**: Traversing link fields within child tables (e.g. `actions.process_name.description`) is natively unsupported by `frappe.qb.get_query`. Direct child queries or multi-action sub-queries should be recommended for child link references.
