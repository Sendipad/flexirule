# FlexiRule "Query Records" Configuration-to-Runtime Matrix

## 1. Complete Field Matrix

| Config Field | Frontend Exists | Serialized | Backend Reads | Passed to Frappe | Runtime Effect | Default | Status |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| **`action_type`** | YES | YES | YES | NO | Dispatches to `QueryRecordsHandler` | `"Query Records"` | **VALID** |
| **`operation`** | YES | YES | YES | NO | Selects mode handler (`_query_list`, `_query_doc`, etc.) | `"Query List"` | **VALID** |
| **`reference_doctype`** | YES | YES | YES | YES | Target DocType for `frappe.get_list()` / metadata checks | `""` | **VALID** |
| **`reference_docname`** | YES | YES | YES | NO | Stored by UI in Query Report mode as Report Name | `""` | **AMBIGUOUS** (UI uses for Report Name, backend `_query_report` checks `config.report_name`) |
| **`ignore_permissions`** | YES | YES | YES | YES | Bypasses read permissions in Frappe calls if user authorized | `0` | **VALID** |
| **`permission_audit_reason`** | YES | YES | YES | NO | Required audit justification string for `ignore_permissions` | `""` | **VALID** |
| **`filters`** | YES | YES | YES | YES | Filter expressions passed to `frappe.get_list(filters=...)` | `[]` | **VALID** |
| **`or_filters`** | NO | NO | YES | YES | Supported by backend normalization, absent from UI | `[]` | **BACKEND ONLY** |
| **`fields`** | YES | YES | YES | YES | Field list passed to `frappe.get_list(fields=...)` | `["name"]` | **VALID** |
| **`order_by`** | YES | YES | YES | YES | Sorting expression passed to `frappe.get_list(order_by=...)` | `"modified desc"` | **VALID** |
| **`limit_type`** | YES | YES | YES | NO | Controls limit computation (`All` -> `0`, `First Record` -> `1`, `Custom Limit`) | `"Custom Limit"` | **VALID** |
| **`limit`** | YES | YES | YES | YES | SQL row limit passed as `limit_page_length` to `frappe.get_list` | `20` | **VALID** |
| **`limit_start` / `offset`** | NO | NO | NO | NO | Pagination start offset is not exposed or supported | N/A | **MISSING** |
| **`group_by`** | YES | YES | YES | YES | Grouping field passed to `frappe.get_list(group_by=...)` | `""` | **VALID** |
| **`distinct`** | YES | YES | YES | YES | Enables row deduplication via `frappe.get_list(distinct=True)` | `0` | **VALID** |
| **`parent_doctype`** | YES | YES | YES | YES | Parent DocType passed when querying child tables directly | `""` | **VALID** |
| **`return_type`** | YES | YES | YES | NO | UI allows "Single Record" / "Full Document", backend always calls `.as_dict()` | `"List of Records"` | **IGNORED BY BACKEND** |
| **`fetch_strategy`** | YES | YES | YES | NO | Controls `Query Doc` document retrieval strategy | `"Get doc"` | **VALID** |
| **`doctype_name`** | YES | YES | YES | NO | Dynamic DocType expression for `Query Doc` | `""` | **VALID** |
| **`docname`** | YES | YES | YES | NO | Dynamic Document ID expression for `Query Doc` | `""` | **VALID** |
| **`report_name`** | YES | YES | YES | YES | Report name passed to `frappe.desk.query_report.run()` | `""` | **VALID** |

---

## 2. Analysis of Field Statuses

### A. Valid Fields (Fully Integrated)
- `filters`, `fields`, `order_by`, `limit_type`, `limit`, `group_by`, `distinct`, `parent_doctype`, `fetch_strategy`, `doctype_name`, `docname`, `ignore_permissions`, `permission_audit_reason`.
- These fields travel seamlessly from Vue UI inputs -> JSON config serialization -> backend parser -> Frappe API invocation with expected runtime effects.

### B. Ignored Fields
- **`return_type` in `Query Doc`**:
  - **Contract**: In `get_operation_contracts()`, `Query Doc` offers options `["Single Record", "Full Document"]`.
  - **Behavior**: `_query_doc` loads the document and unconditionally executes `return doc.as_dict()`. The returned data structure is identical regardless of which option is chosen.

### C. Backend-Only Capabilities (Missing UI Controls)
- **`or_filters`**: Supported in `query_records.py` (`_resolve_query_filters()` handles `or_filters` and passes them to `frappe.get_list(or_filters=...)`), but `QueryRecordsConfig.vue` and `FilterGroup.vue` only support standard AND filter groups.
- **`limit_start` / `offset`**: Supported natively by Frappe's `DatabaseQuery`, but not present in `QueryRecordsConfig.vue` or `_query_list()`.

### D. Mismatched / Ambiguous Contracts
- **`reference_docname` in `Query Report`**:
  - Frontend stores the report name in `node.data.reference_docname` (and also duplicates it to `config.report_name`).
  - Backend `_query_report` checks `config.get("report_name")`, but `get_operation_contracts()` specifies `reference_docname` as required for `Query Report`.
