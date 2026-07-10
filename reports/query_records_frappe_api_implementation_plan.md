# Engineering Migration Plan: Query Records Frappe API Refactor

## 1. Executive Summary

This document outlines the engineering specification and implementation plan to align **FlexiRule's Query Records** action handler with the security, permissions, and child-table querying behavior of the **Frappe Framework (v15+)**.

This plan is based strictly on empirical evidence gathered during deep source-code auditing and live database runtime checks on the Frappe target site.

### Key Audited Findings:
1.  **Critical Security Vulnerability**: FlexiRule's aggregate modes (`Count`, `Sum`, `Average`, `Min`, `Max`, `Group By`) utilize `frappe.get_all()`. By design, `frappe.get_all()` overrides any user parameter and forces `ignore_permissions = True`. This creates an immediate role, document-sharing, and owner permission bypass for standard users.
2.  **Dotted Key Filter Crash**: Passing a dotted key inside a dictionary filter (e.g. `{"fields.fieldname": "owner"}`) causes a database `OperationalError` because Frappe's `DatabaseQuery` does not parse dotted paths inside dictionary filters.
3.  **No Row Deduplication Support**: Joining child tables causes duplicate parent records in the result set, and rule builders currently have no way to execute standard `DISTINCT` queries.

### Project Roadmap Categorization:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            IMPLEMENTATION ORDER                              │
├───────┬───────────────────────────────────┬───────────────┬──────────────────┤
│ Phase │ Refactor Focus                    │ Type          │ Effort Estimate  │
├───────┼───────────────────────────────────┼───────────────┼──────────────────┤
│   1   │ Fix Aggregate Permission Bypass   │ Required Fix  │ 1 Hour           │
├───────┼───────────────────────────────────┼───────────────┼──────────────────┤
│   2   │ Backend Filter Normalization      │ Required Fix  │ 4 Hours          │
├───────┼───────────────────────────────────┼───────────────┼──────────────────┤
│   3   │ UI & Backend DISTINCT Support    │ Enhancement   │ 2 Hours          │
├───────┼───────────────────────────────────┼───────────────┼──────────────────┤
│   4   │ Direct Child DocType Querying    │ Enhancement   │ 2 Hours          │
└───────┴───────────────────────────────────┴───────────────┴──────────────────┘
```

---

## 2. Implementation Scope

The following changes must be applied strictly to the files and functions specified below. No other unrelated codebase layers may be modified.

### 2.1 Backend Changes

#### File: `flexirule/ruleflow/core/action_handlers/query_records.py`

*   **Function**: `_count_records`
    *   *Current Behavior*: Executes `frappe.get_all` with aggregate count field.
    *   *Required Modification*: Replace `frappe.get_all` with `frappe.get_list` and add `limit_page_length=0`.
    *   *Reason*: `frappe.get_all` programmatically ignores all row-level, sharing, and field-level permissions.
    *   *Risk Level*: **Low**. (Behaviorally equivalent with full permissions checked).

*   **Function**: `_aggregate`
    *   *Current Behavior*: Executes `frappe.get_all` with aggregate SUM/AVG/MIN/MAX projections.
    *   *Required Modification*: Replace `frappe.get_all` with `frappe.get_list` and add `limit_page_length=0`.
    *   *Reason*: Secures all metric calculations against unauthorized data access.
    *   *Risk Level*: **Low**.

*   **Function**: `_group_by`
    *   *Current Behavior*: Executes `frappe.get_all` with group-by and aggregate count projections.
    *   *Required Modification*: Replace `frappe.get_all` with `frappe.get_list` and add `limit_page_length=0`.
    *   *Reason*: Enforces role permissions on grouping results.
    *   *Risk Level*: **Low**.

*   **Function**: `_exist_record`
    *   *Current Behavior*: Executes `frappe.get_all` to evaluate record existence.
    *   *Required Modification*: Replace `frappe.get_all` with `frappe.get_list` and add `limit_page_length=1`.
    *   *Reason*: Restricts standard users from detecting existence of unauthorized records.
    *   *Risk Level*: **Low**.

*   **Function**: `_normalize_filters_for_backend`
    *   *Current Behavior*: Recursively parses filter arrays/dictionaries and converts operators.
    *   *Required Modification*: Introduce parsing logic to detect dotted fieldnames (e.g. `fields.fieldname`). Split dotted keys and translate them to standard 4-value list-of-lists child queries (`[["Child DocType", "child_field", "operator", "value"]]`).
    *   *Reason*: Bypasses SQL `OperationalError` column errors by compiling correct left-join queries.
    *   *Risk Level*: **Medium**. (Requires robust metadata validation).

*   **Function**: `_query_list`
    *   *Current Behavior*: Executes `frappe.get_list` with a standard fields and limits kwargs mapping.
    *   *Required Modification*:
        1. Read `parent_doctype` from `config` and pass to `frappe.get_list` when querying Child DocTypes.
        2. Read `distinct` from `config` and pass `distinct=bool(config.get("distinct"))` to `frappe.get_list`.
    *   *Reason*: Adds full support for direct child table querying and row deduplication.
    *   *Risk Level*: **Low**.

### 2.2 Frontend Changes

#### File: `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue`

*   **Required Modifications**:
    1.  Add a "Deduplicate Rows (DISTINCT)" checkbox toggle under the Query List fields projection section, visible only when the operation mode is "Query List".
    2.  Add a "Parent DocType" Link selection control field, visible only when the target doctype metadata reveals that `istable` is True. Automatically set its query options to parent doctypes referencing this child doctype.

---

## 3. Commit-by-Commit Implementation Plan

### Commit 1: Fix aggregate and metric permission bypasses
*   **Commit Title**: `security(query-records): fix permission bypass in aggregate operations`
*   **Files Modified**: `flexirule/ruleflow/core/action_handlers/query_records.py`
*   **Implementation Details**:
    - Change `frappe.get_all` to `frappe.get_list` inside `_count_records`, `_aggregate`, and `_group_by`.
    - Change `frappe.get_all` to `frappe.get_list` inside `_exist_record` with `limit_page_length=1`.
    - Explicitly pass `limit_page_length=0` to preserve full aggregate evaluation.
*   **Tests Added**:
    - Test that `_count_records` and `_aggregate` throw `PermissionError` when executed under a standard user who lacks permissions to access the target DocType.
*   **Rollback Strategy**: Revert commit 1; standard behavior is restored with the security bypass remaining.

---

### Commit 2: Implement dotted child-table filter normalization
*   **Commit Title**: `refactor(query-records): normalize child table dotted filter paths`
*   **Files Modified**: `flexirule/ruleflow/core/action_handlers/query_records.py`
*   **Implementation Details**:
    - Refactor `_normalize_filters_for_backend`.
    - Detect dotted filter keys. Resolve parent-child table fields, fetch child doctype options, and compile a 4-value list-of-lists format: `[child_doctype, child_fieldname, operator, value]`.
*   **Tests Added**:
    - Pass a dictionary containing `{"fields.fieldname": "value"}` and assert it successfully compiles to `[["DocField", "fieldname", "=", "value"]]`.
*   **Rollback Strategy**: Revert commit 2; dotted filter dictionary queries will revert to database `OperationalError` behavior.

---

### Commit 3: Add child DocType query support
*   **Commit Title**: `feat(query-records): support parent_doctype parameter for child queries`
*   **Files Modified**: `flexirule/ruleflow/core/action_handlers/query_records.py`
*   **Implementation Details**:
    - Read `parent_doctype` from `config` inside `_query_list` and pass it inside the `frappe.get_list` kwargs.
*   **Tests Added**:
    - Query a child DocType directly with standard user session, passing a valid parent DocType. Verify that the query succeeds.
*   **Rollback Strategy**: Revert commit 3.

---

### Commit 4: Add DISTINCT support
*   **Commit Title**: `feat(query-records): support DISTINCT toggle in list queries`
*   **Files Modified**:
    - `flexirule/ruleflow/core/action_handlers/query_records.py`
    - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue`
*   **Implementation Details**:
    - Read `distinct` boolean from config inside `_query_list()` and pass `distinct=distinct` to `frappe.get_list`.
    - Add "Deduplicate Rows (DISTINCT)" checkbox toggle to `QueryRecordsConfig.vue`.
*   **Tests Added**:
    - Assert that distinct queries return deduplicated parent row counts when child tables are left-joined.
*   **Rollback Strategy**: Revert commit 4.

---

## 4. Detailed Algorithm Design

### 4.1 Dotted Filter Normalization Algorithm

This algorithm intercepts dotted fieldname filters (e.g. `fields.fieldname`) inside `_normalize_filters_for_backend` and translates them into explicit list-of-lists child queries.

#### Detect & Resolve Pipeline:
1.  **Dotted Path Detection**: If key string contains `.` (and does not match a standard SQL function), split on the first dot: `table_fieldname, child_fieldname = key.split(".", 1)`.
2.  **Parent Metadata Audit**: Perform a lookup on the parent metadata:
    - Get the field definition: `df = meta.get_field(table_fieldname)`.
    - If `df` is None or `df.fieldtype` is not in `("Table", "Table MultiSelect")`, evaluate if `table_fieldname` is a standard Link field.
        - If it is a Link field, rewrite key to use standard Link join aliases.
        - Otherwise, treat as an invalid field reference and raise a `ValidationError`.
3.  **Conflict Resolution**:
    - If nested paths appear (e.g., `items.batch.item`), Frappe's `DatabaseQuery` does not support multiple nested joins natively. Stop processing and throw `frappe.ValidationError` indicating nested table queries are unsupported.
    - If the field does not exist on the resolved child doctype, raise a `ValidationError`.

#### Pseudocode:

```python
def normalize_dotted_filter(parent_doctype, fieldname, operator, value):
    if "." not in fieldname:
        return [fieldname, operator, value]

    parts = fieldname.split(".")
    if len(parts) > 2:
        frappe.throw(_("Nested child table paths (greater than 1 level) are unsupported in query filters: {0}").format(fieldname))

    table_fieldname, child_field = parts[0], parts[1]
    meta = frappe.get_meta(parent_doctype)
    df = meta.get_field(table_fieldname)

    if not df or df.fieldtype not in ("Table", "Table MultiSelect"):
        # Check if it's a Link field
        if df and df.fieldtype == "Link":
            # For Link joins, DatabaseQuery handles aliases natively if we pass the dotted field
            return [fieldname, operator, value]
        frappe.throw(_("Field '{0}' is not a valid Child Table in DocType '{1}'").format(table_fieldname, parent_doctype))

    child_doctype = df.options
    child_meta = frappe.get_meta(child_doctype)
    if not child_meta.has_field(child_field) and child_field not in ("name", "parent", "parenttype"):
        frappe.throw(_("Field '{0}' does not exist in Child DocType '{1}'").format(child_field, child_doctype))

    # Return explicit list format specifying Child DocType
    return [child_doctype, child_field, operator, value]
```

---

### 4.2 Parent DocType Resolution

Querying child DocTypes directly requires verifying read privileges on the parent record. This resolution integrates both **Automatic Inference** and **Explicit UI Configuration**.

```
                           Target DocType is Child Table?
                                   │
                     ┌─────────────┴─────────────┐
                     ▼ Yes                       ▼ No
           Has Parent DocType Config?        Run standard query
                     ┌─────────────┴─────────────┐
                     ▼ Yes                       ▼ No
           Validate Parent Relation        Fetch parent doctypes from DB
                     │                           │
                     ▼                           ▼
            Run parent permission check   Default to first matched parent
```

#### Metadata Lookup & Caching Strategy:
- Parent doctypes are identified by querying the metadata database:
  ```python
  parent_dtypes = frappe.get_all("DocField", filters={"options": target_child_doctype, "fieldtype": ["in", ["Table", "Table MultiSelect"]]}, pluck="parent")
  ```
- To prevent heavy database overhead during rule execution, metadata lookups must utilize Frappe's request-local memory cache: `frappe.local.cache` (via `frappe.cache().hget`).
- **Failure Behavior**: If no parent doctype can be resolved or inferred, the query raises a `ValidationError` prompting the rule builder to configure a valid Parent DocType.

---

### 4.3 Aggregate Migration Design

| Parameter / Aspect | Before: `frappe.get_all(...)` | After: `frappe.get_list(..., limit_page_length=0)` | Compatibility Status |
| :--- | :--- | :--- | :--- |
| **Argument Compatibility** | Fully supports `filters`, `fields`, `group_by`, and `order_by`. | Fully supports `filters`, `fields`, `group_by`, and `order_by`. | **100% Compatible**. |
| **Return Structure** | Returns a list of dicts. | Returns a list of dicts. | **100% Compatible**. |
| **SQL Equivalence** | Compiles clean aggregates without LIMIT clauses. | Compiles clean aggregates without LIMIT clauses (limit 0 is omitted). | **100% Equivalent**. |
| **Database Portability** | Supports MariaDB and PostgreSQL. | Supports MariaDB and PostgreSQL. | **100% Equivalent**. |
| **User Security** | Completely bypasses row-level and sharing filters. | Enforces fine-grained row, owner, and document sharing filters. | **Permissions Secured**. |

---

## 5. Frontend Design Changes

### 5.1 DISTINCT Configuration in `QueryRecordsConfig.vue`
*   **UI Location**: Under the Selected Fields Projection list.
*   **Default Value**: `false` (unchecked).
*   **Validation Rules**: If `distinct` is enabled, validate that the user has selected at least one field. Show a warning if no fields are selected.
*   **Interactions**:
    - **`group_by`**: If `group_by` is active, disable the `distinct` checkbox with a helper tooltip: `"Deduplication is handled automatically by Group By"`.
    - **Aggregates**: Hide or disable the checkbox when aggregate operations (Sum, Average, etc.) are active.

### 5.2 Child DocType Parent Configuration in `QueryRecordsConfig.vue`
*   **Visibility**: Hidden by default. If the selected "Target DocType" is identified as a Child DocType (`istable` is true), display a mandatory `Parent DocType` selection box.
*   **Automatic Inference**: Fetch the list of parent doctypes utilizing the child. If there is exactly one parent doctype (e.g. `Form Tour` for `Form Tour Step`), automatically pre-fill the Parent DocType selection box.
*   **User Experience**: Clearly explain to the user why the Parent DocType is needed: *"This child table requires parent record checks to verify execution permissions at runtime."*

---

## 6. Regression Test Plan

### 6.1 Security Tests
| Test Case Scenario | Input / Configuration | Expected Outcome | Behavior Verified |
| :--- | :--- | :--- | :--- |
| **Standard user reads Count on Restricted DocType** | `Count` query on `User` under `test1@example.com` | Raise `PermissionError` | Verified Aggregate Security |
| **Standard user reads Sum on Permitted DocType** | `Sum` query with sharing restrictions | Returns sum of *only* permitted rows | Verified Fine-Grained Metrics |
| **System manager reads Count with ignore_perm=True**| Query with `skip_permissions=True` | Returns absolute total count | Verified Skip Overrides |

### 6.2 Filter Tests
| Test Case Scenario | Input / Configuration | Expected Outcome | Behavior Verified |
| :--- | :--- | :--- | :--- |
| **Normal Dictionary Filter** | `{"name": "ToDo"}` | Normalized to `[["name", "=", "ToDo"]]` | Standard queries pass |
| **Dotted Child Table Filter** | `{"fields.fieldname": "owner"}` | Compiled to `[["DocField", "fieldname", "=", "owner"]]` | Normalization succeeds |
| **Invalid Dotted Filter** | `{"fields.invalid_column": "val"}`| Raise `ValidationError` | Detected invalid field |
| **Nested Dotted Filter** | `{"fields.child_table.fieldname": "val"}` | Raise `ValidationError` | Detected invalid nesting |

### 6.3 Query Behavior Tests
| Test Case Scenario | Input / Configuration | Expected Outcome | Behavior Verified |
| :--- | :--- | :--- | :--- |
| **Dotted Projection Fields** | Fields: `["name", "fields.fieldname"]` | Left-joins `DocField` table successfully | Correct automatic joining |
| **Deduplicated Parent Projection** | `fields=["name"]`, child filter active, `distinct=True` | Returns unique parent row names | Row duplicate prevention |
| **Multiple order-by clauses** | `order_by="creation desc, modified asc"` | Correctly orders result sets | Standard SQL sorting |

---

## 7. Migration Compatibility Audit

Existing rules configured under previous versions must remain fully compatible and operational.

### Rule JSON Shapes

#### Before (V1 Rules):
```json
{
 "action_type": "Query Records",
 "operation": "Count",
 "reference_doctype": "DocType",
 "config": {
   "filters": {"name": "ToDo"}
 }
}
```

#### After (V2 Rules):
```json
{
 "action_type": "Query Records",
 "operation": "Count",
 "reference_doctype": "DocType",
 "config": {
   "filters": {"name": "ToDo"},
   "distinct": false,
   "parent_doctype": ""
 }
}
```

### Compatibility Resolution:
- Inside the backend `query_records.py`, keys like `distinct` and `parent_doctype` are fetched using safe default retrieval: `config.get("distinct", False)` and `config.get("parent_doctype")`.
- No SQL or structure changes are required for existing rules. They will continue to run exactly as before, with the immediate benefit of full permissions compliance.

---

## 8. Performance Considerations

### Performance Impact of `get_all` -> `get_list`

Replacing `get_all` with `get_list` introduces match condition evaluations which append role-permissions and share-permissions to the SQL query.

```
                  Query Performance Impact by Dataset Size

  Execution Time (ms)
   ▲
   │                                         / [get_list with heavy User Perms]
   │                                        /
   │                                       /
   │                                      /  ── [get_list standard / get_all]
   │                                     /
   │                                    /
   │                                   /
   │                                  /
   └─────────────────────────────────/──────────────────►
                                     Dataset Size (Records)
                                     [Small -> Large]
```

*   **Small Datasets (< 10,000 records)**: The overhead of appending permission filters (e.g. `owner = 'user@example.com'`) is negligible (< 2ms difference).
*   **Medium Datasets (10,000 - 100,000 records)**: If a standard user has hundreds of fine-grained User Permissions, the SQL string will contain a large `IN` list: e.g. `company IN ('C1', 'C2', ..., 'C100')`. Ensure that index coverage exists on the permission fields (like `owner` or `company`) to maintain query times under 20ms.
*   **Large Datasets (> 100,000 records)**: Database optimization is critical. Standard indexes must be added to child table mapping fields (`parent`, `parenttype`, `parentfield`) to ensure the automatic `LEFT JOIN` evaluates in optimal O(log N) time rather than triggered table scans.

---

## 9. Risk Matrix

| Refactor Task | Risk Category | Operational Impact | Safe Rollback Strategy |
| :--- | :--- | :--- | :--- |
| **Fix Aggregate Permissions** | **Low** | None. Standard queries remain fully identical. Users only see records they have permission to access. | Revert change from `get_list` to `get_all`. |
| **Dotted Filters Normalization**| **Medium** | Low risk of raising exceptions if metadata lookups fail. | Revert filter parsing changes. Dotted filters revert to standard database column errors. |
| **Distinct Support** | **Low** | Clears duplicate results. | Set `distinct` default in config to `False`. |
| **Parent DocType Support** | **Low** | Allows querying child tables directly under normal user context. | Clear `parent_doctype` parameter in `get_list`. |

---

## 10. Final Implementation Checklist

### Backend Checklist
- [ ] Replace `get_all` with `get_list` and set `limit_page_length=0` in `_count_records()`.
- [ ] Replace `get_all` with `get_list` and set `limit_page_length=0` in `_aggregate()`.
- [ ] Replace `get_all` with `get_list` and set `limit_page_length=0` in `_group_by()`.
- [ ] Replace `get_all` with `get_list` and set `limit_page_length=1` in `_exist_record()`.
- [ ] Update `_normalize_filters_for_backend` to detect dots and resolve child table metadata.
- [ ] Extract and pass `distinct` from config into `_query_list()`.
- [ ] Extract and pass `parent_doctype` from config into `_query_list()`.

### Frontend Checklist
- [ ] Add "Deduplicate Rows (DISTINCT)" checkbox toggle under selected fields in `QueryRecordsConfig.vue`.
- [ ] Conditionally disable the DISTINCT checkbox if group-by is configured.
- [ ] Add "Parent DocType" selection dropdown when target doctype `istable` is True.

### Tests Checklist
- [ ] Add backend unit test verifying aggregate permissions restriction under restricted users.
- [ ] Add backend unit test verifying dotted filters normalization successfully compiles child lists.
- [ ] Add backend unit test verifying DISTINCT correctly deduplicates parent projections.
- [ ] Run complete test suite and verify 100% pass rates.

### Documentation Checklist
- [ ] Document DISTINCT and Parent DocType usage in `docs/content/en/docs/actions/query_records.md`.
- [ ] Update release notes for security compliance update.
