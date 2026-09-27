# Frontend ↔ Backend Contract Audit

## 1. Overview

The contract between the frontend Vue components (`QueryRecordsConfig.vue`, `ConfigurationPanel.vue`) and backend Python handlers (`query_records.py`, `base_contract.py`) defines how user configurations are validated, serialized, and executed. This audit compares both layers to identify schema drift and contract mismatches.

---

## 2. Identified Schema & Contract Mismatches

### Mismatch 1: `return_type` in `Query Doc` Mode
- **Backend Operation Contract (`base_contract.py` / `query_records.py`)**:
  Defines `return_type` with options `["Single Record", "Full Document"]`.
- **Frontend Contract (`QueryRecordsConfig.vue`)**:
  UI exposes the dropdown for `return_type` when `operation == "Query Doc"`.
- **Backend Runtime (`_query_doc`)**:
  The handler ignores `action.return_type` entirely and unconditionally executes `return doc.as_dict()`. The returned data structure is identical regardless of the selection.

### Mismatch 2: `reference_docname` vs `report_name` in `Query Report` Mode
- **Backend Operation Contract**:
  Specifies `{"fieldname": "reference_docname", "label": "Report Name", "options": "Report", "reqd": 1}` as a required field for `Query Report`.
- **Frontend Component (`QueryRecordsConfig.vue`)**:
  Stores report name in `node.data.reference_docname` AND duplicates it into `config.report_name`.
- **Backend Handler (`_query_report`)**:
  Reads `report_name = config.get("report_name")` and throws `frappe.throw(_("report_name is required in config..."))` if missing, ignoring `action.reference_docname`.

### Mismatch 3: `or_filters` Availability
- **Backend Contract**:
  `query_records.py` contains full support for `or_filters` in `_resolve_query_filters()` and passes `or_filters` to `frappe.get_list()`.
- **Frontend Component**:
  `QueryRecordsConfig.vue` and `FilterGroup.vue` render controls exclusively for AND filters. There is no UI mechanism for users to construct OR filter groups.

### Mismatch 4: Default Limit Discrepancy
- **Frontend Component (`QueryRecordsConfig.vue`)**:
  `load_local_config()` defaults `config.limit = 20` when mode is `Query List`.
- **Backend Handler (`_query_list`)**:
  If `config.get("limit")` is empty or `None`, falls back to `20`.
- **Native Frappe Default**:
  `frappe.get_list()` defaults `limit_page_length` to `20`. `frappe.get_all()` defaults to `0` (unlimited).

---

## 3. Backward Compatibility & Legacy Normalization

In `flexirule/patches/v1_0/migrate_deprecated_action_types.py` and `flexirule/patches/normalize_action_type_aliases.py`:
- Legacy action type `"Aggregate Records"` is automatically migrated to `"Query Records"`.
- Deprecated operation names are normalized during migration.
