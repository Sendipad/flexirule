# Detailed Inventory of Audit Findings

## Finding Summary by Severity

| ID | Title | Severity | Layer Affected | Source Reference |
| :--- | :--- | :---: | :--- | :--- |
| **F-01** | `return_type="Full Document"` returns `dict`, not `Document` instance | **MEDIUM** | Backend Action Handler | `query_records.py` (lines 1115-1124) |
| **F-02** | Absence of pagination offset (`limit_start` / `offset`) | **MEDIUM** | Frontend & Backend | `QueryRecordsConfig.vue`, `query_records.py` |
| **F-03** | In-memory overhead in `Query Doc` via `doc.as_dict()` | **MEDIUM** | Performance / ORM | `query_records.py` (`_query_doc`) |
| **F-04** | `reference_docname` vs `report_name` schema conflict in `Query Report` | **LOW** | Action Contract & Vue | `QueryRecordsConfig.vue`, `base_contract.py` |
| **F-05** | Lack of Vue UI controls for `or_filters` | **LOW** | Frontend UI | `QueryRecordsConfig.vue`, `FilterGroup.vue` |
| **F-06** | Native MultiSelectList serialization in Query Report | **INFO** | Filter Normalization | `query_records.py` (`_query_report`) |

---

## Detailed Finding Descriptions

### F-01: `return_type="Full Document"` Returns `frappe._dict`, Not `Document` Instance
- **Severity**: Medium (Architectural / Contract Drift)
- **Layer**: `QueryRecordsHandler._query_doc()`
- **Source Reference**: `flexirule/ruleflow/core/action_handlers/query_records.py`
- **Description**:
  The UI and operation contract allow users to select `return_type: "Full Document"`. However, `_query_doc()` executes `return doc.as_dict()`, stripping active ORM methods (`save()`, `submit()`, `db_set()`). Sub-actions cannot invoke ORM methods on context variables created by `Query Doc`.
- **Impact**: Misleading configuration contract; downstream actions expecting a `Document` object receive a dictionary instead.

### F-02: Absence of Pagination Offset (`limit_start` / `offset`)
- **Severity**: Medium (Feature Gap)
- **Layer**: `QueryRecordsConfig.vue` & `query_records.py._query_list()`
- **Source Reference**: `QueryRecordsConfig.vue` & `query_records.py`
- **Description**:
  Frappe's `DatabaseQuery` supports `limit_start` (SQL `OFFSET`). Neither the Vue UI nor `_query_list()` accepts or passes `limit_start`.
- **Impact**: Rule authors cannot paginate through large record sets in chunks.

### F-03: Performance Overhead in `Query Doc` via `doc.as_dict()`
- **Severity**: Medium (Performance)
- **Layer**: Backend Handler (`_query_doc`)
- **Source Reference**: `flexirule/ruleflow/core/action_handlers/query_records.py`
- **Description**:
  `_query_doc()` calls `frappe.get_doc()`, fetching all child table rows, attachment metadata, and running controller hooks, only to immediately call `.as_dict()`. When a rule only needs scalar fields from a single document, this produces unnecessary database queries and CPU overhead.
- **Impact**: N+1 query amplification if `Query Doc` is run inside a loop.

### F-04: `reference_docname` vs `report_name` Schema Mismatch
- **Severity**: Low (Contract Consistency)
- **Layer**: Frontend Component & Backend Handler
- **Source Reference**: `QueryRecordsConfig.vue` & `query_records.py`
- **Description**:
  In `Query Report` mode, `base_contract.py` specifies `reference_docname` as the report name field. However, `_query_report()` checks `config.get("report_name")`. The Vue UI duplicates the value into both keys to bypass the discrepancy.
- **Impact**: Contract ambiguity across frontend and backend.
