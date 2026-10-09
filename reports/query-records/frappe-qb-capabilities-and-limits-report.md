# Frappe Query Builder (`frappe.qb.get_query`) Evidence-Based Audit & Capabilities Report

## Executive Summary
This report records source-level and empirical observations about Frappe v15's native Query Builder (`frappe.qb.get_query` / `Engine.get_query`) and FlexiRule's **Fetch Records** integration (`QueryRecordsHandler._fetch_records`). The capability probes and FlexiRule integration tests are separate evidence categories: a native QB capability passing does not prove the FlexiRule adapter preserves the input or produces correct results.

The seven dedicated modules below define 39 test methods. **The latest full-app CI run did not pass**, so these tests must not be described as a currently green suite. See the verification status below. Test modules:
1. `test_qb_field_path_capabilities.py` (5 tests) - Reuses installed `Rule`, `Rule Action`, `Process` DocTypes
2. `test_qb_operator_capabilities.py` (6 tests) - Reuses installed `Rule` DocType
3. `test_qb_tree_capabilities.py` (5 tests) - Retains dedicated `QB Tree Node <RUN_ID>` DocType (Tree DocType required)
4. `test_qb_fieldtype_value_matrix.py` (3 tests) - Reuses installed `Rule`, `Data Review Task` DocTypes & retains `QB Matrix Temp <RUN_ID>` fixture for `Date`/`Currency`
5. `test_fetch_records_normalization.py` (4 tests) - Direct unit tests for `QueryRecordsHandler`
6. `test_fetch_records_filter_tree_integration.py` (3 tests) - Reuses installed `Rule` DocType
7. `test_fetch_records.py` (13 tests) - Reuses installed `Rule` & `Rule Action` DocTypes

---

## 1. Environment & Execution Context
- **Frappe Version**: Frappe v15.121.1 (`apps/frappe`)
- **Database Backend**: MariaDB / MySQL (InnoDB engine on `test_site`)
- **Test Site**: `test_site` (`/home/jules/frappe-bench`)
- **Test Command**: `bench --site test_site run-tests --app flexirule --module flexirule.ruleflow.tests.<module_name>`
- **Dedicated module inventory**: 39 test methods across the seven listed modules. **Latest verified full-app CI result**: 531 tests run; 10 failures, 1 error, 2 skipped. The CI result does not support a claim that all 39 dedicated tests pass.

### Latest CI verification — 2026-10-09

- **Workflow run:** [GitHub Actions run 37971338723](https://github.com/Sendipad/flexirule/actions/runs/37971338723)
- **Result:** failed in the Server job; `Ran 531 tests in 16.111s`; `FAILED (failures=10, errors=1, skipped=2)`.
- **Failing integration coverage:** ten failures in `test_fetch_records.py` (default fields, canonical filter conversion, child-table filtering, dynamic values, aliases, boolean coercion, starts/ends-with, ordinary operators, nested AND/OR, and ordering/limit/offset).
- **Error:** `test_02_three_level_deep_logical_tree_execution` in `test_fetch_records_filter_tree_integration.py`; stack enters `frappe_query_compat._compile_logical_filters()` and `_criterion_for_leaf()`.
- **Interpretation:** the native capability modules may characterize individual Frappe behaviors, but the end-to-end Fetch Records adapter is not verified as correct while this run is red. Do not use this run as evidence that Fetch Records is production-ready.
- **Scope caution:** current `query_records.py` recursively resolves the whole filter payload and falls back to `_normalize_filters_for_backend()` for non-canonical lists/dicts. This conflicts with the intended canonical-tree-only contract for the new Fetch Records mode and can blur the boundary between new-mode behavior and legacy Query Records modes. Keep legacy normalization for established modes, but do not route Fetch Records through that fallback.

---

## 2. Test Safety, Fixture Isolation & Zero Deletion-on-Collision Architecture
To guarantee that running tests never delete pre-existing site data, DocTypes, or shared records:
- **Reuse Installed FlexiRule DocTypes**:
  - `Rule`, `Rule Action`, `Process`, and `Data Review Task` are reused across operator capability, filter tree integration, field path capability, and value matrix tests.
  - Reused fields include `rule_name`, `is_active`, `execution_mode`, `priority`, `max_execution_time`, `description`, `resolved_on`, `actions.action_id`, and `process_name.description`.
- **Justified Dedicated Fixtures**:
  - `QB Tree Node <RUN_ID>`: Retained as a uniquely named per-run test DocType because no installed FlexiRule DocType has `is_tree: 1` required to test tree hierarchy operators (`descendants of`, `ancestors of`, etc.).
  - `QB Matrix Temp <RUN_ID>`: Retained as a uniquely named per-run test DocType strictly to cover `Date` and `Currency` fieldtypes not present on installed FlexiRule DocTypes.
- **Zero Deletion-on-Collision & Explicit Ownership Tracking**:
  - Setup-time deletions (`frappe.delete_doc` / `frappe.db.delete` on pre-existing records) have been completely eliminated.
  - Each test run generates a unique hex suffix (`_run_id = uuid.uuid4().hex[:8].upper()`) for its test documents and dedicated DocTypes.
  - If a document or DocType with the generated test name unexpectedly already exists, the test fails fast (`RuntimeError`) rather than silently deleting or reusing pre-existing site data.
  - Queries match test data using explicit created document name lists (`["rule_name", "in", [name1, name2, ...]]`) rather than fuzzy SQL `LIKE` wildcards with `_`.
  - `tearDownClass` deletes ONLY test-owned records and test-created DocTypes in reverse creation order, preserving pre-existing site records and shared metadata.

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
| `descendants of` | **Supported** | Direct | Evaluates Tree DocType `lft` and `rgt` on `QB Tree Node <RUN_ID>` |
| `ancestors of` | **Supported** | Direct | Evaluates Tree DocType `lft` and `rgt` on `QB Tree Node <RUN_ID>` |
| `starts with` / `ends with` | Unsupported | Normalized | Converted to `like "val%"` / `like "%val"` (see double-wildcarding note) |
| `Between` / `Timespan` | Unsupported | Normalized | Coerced to `between [start, end]` |

---

## 5. Summary & Release Recommendations
1. **Fixture isolation**: the inspected dedicated fixtures use run-specific names and track created records. This is a source review of cleanup behavior, not a claim that the latest CI run passed; keep test-owned-resource cleanup paired with fail-fast collision checks.
2. **Dotted Path UI Depth**: UI ComboBox controls for Fetch Records should constrain dotted field navigation to 1 link level or direct child table level, as >1 level dotted chains trigger `ValueError: too many values to unpack` in `frappe.qb.get_query`.
3. **Double Wildcarding**: Users configuring `starts with` in FlexiRule who manually enter a `%` suffix will produce `%%`. A separate focused change may be considered if wildcard sanitization is desired.
4. **Child Table Link Fields**: Traversing link fields within child tables (e.g. `actions.process_name.description`) is natively unsupported by `frappe.qb.get_query`. Direct child queries or multi-action sub-queries should be recommended for child link references.
