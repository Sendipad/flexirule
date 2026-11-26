# Test Coverage Audit & Proposed Test Scenarios

## 1. Existing Test Suite Inventory

FlexiRule contains three primary test suites covering Query Records:
1. `flexirule/ruleflow/tests/test_query_records_refactor.py` (Tests `Query List`, `Query Doc`, `Exist Record`, `Count`, `Sum`, `Average`, `Min`, `Max`, `Group By`, and `ignore_permissions`).
2. `flexirule/ruleflow/tests/test_query_records_filters.py` (Tests filter normalization, operators, dynamic expression evaluation).
3. `flexirule/ruleflow/tests/test_query_report_serialization.py` (Tests `Query Report` filter serialization and execution).

---

## 2. Test Coverage Gaps

While core happy-path scenarios are well covered, several key architectural contracts lack unit/integration testing:
1. **Field Projection (`fields` parameter)**: No test verifies that passing `fields=["name", "status"]` strictly excludes other columns from the result set dictionary.
2. **`return_type` Contract in `Query Doc`**: No test verifies behavioral differences between `return_type="Single Record"` and `return_type="Full Document"`.
3. **`order_by` Table Qualification**: No test verifies that complex multi-field `order_by` strings containing child table dot-notation (`items.qty desc`) are correctly qualified without throwing SQL syntax errors.
4. **`ignore_permissions` Role Check**: No test asserts that a non-System Manager user attempting to run `ignore_permissions=1` raises a `frappe.PermissionError`.

---

## 3. Proposed Concrete Test Scenarios

### Test Scenario 1: Field Selection Projections in Query List
- **Given**: A DocType with 10 fields (e.g. `Sales Order`).
- **When**: Executing `Query List` with `fields = ["name", "grand_total"]`.
- **Then**: Returned list of dicts should contain keys `{"name", "grand_total"}` and **exclude** all other fields.
- **Expected Frappe behavior**: `frappe.get_list` projects only selected columns.
- **Expected FlexiRule behavior**: Passes `fields` directly to `frappe.get_list`.
- **Current Result**: Passes `fields` correctly, but unvalidated in test suite.
- **Gap**: Missing assertion in `test_query_records_refactor.py`.

### Test Scenario 2: Permission Override Guard Verification
- **Given**: An active user without `System Manager` or `Rule Builder` role.
- **When**: Executing `Query Records` action with `ignore_permissions: 1` and `permission_audit_reason: "Testing"`.
- **Then**: Execution must raise `frappe.PermissionError`.
- **Expected Frappe behavior**: Role-restricted bypass guard.
- **Expected FlexiRule behavior**: `can_ignore_permissions` throws `PermissionError`.
- **Current Result**: Functionality exists in code, but negative role test case is absent.
- **Gap**: Missing role-based negative test case in test suite.

### Test Scenario 3: `Query Doc` Return Type Contract Compliance
- **Given**: A `Query Doc` action configured with `return_type: "Single Record"`.
- **When**: Action is executed against an existing record.
- **Then**: Return shape should match contract expectations.
- **Expected Frappe behavior**: Return scalar fields or document representation.
- **Expected FlexiRule behavior**: Differentiate `Single Record` (scalar fields via `get_list`) vs `Full Document` (full `as_dict()`).
- **Current Result**: Both return full `doc.as_dict()`.
- **Gap**: Behavioral discrepancy between `return_type` contract options.
