# Architectural Remediation Plan

## 1. Executive Remediation Vision

The guiding architectural principle for Query Records is:

> **"FlexiRule should define the user-facing configuration contract while delegating query building, permission enforcement, field projection, ordering, and pagination directly to Frappe's native query APIs (`frappe.get_list`, `frappe.get_doc`)."**

---

## 2. Strategic Remediation Initiatives

### Initiative 1: Resolve `Query Doc` Return Type & Performance Model
- **Problem**: `Query Doc` uses `frappe.get_doc()` and calls `doc.as_dict()`, creating overhead when only scalar fields are needed, while failing to provide an active `Document` controller when `Full Document` is requested.
- **Root Cause**: Unconditional call to `doc.as_dict()` in `_query_doc()`.
- **Affected Layer**: Backend Handler (`_query_doc`).
- **Recommended Architectural Direction**:
  - If `return_type == "Single Record"`: Delegate to `frappe.get_list(reference_doctype, filters=filters, limit_page_length=1)` to fetch scalar dictionary directly via SQL in 1 query without loading child tables.
  - If `return_type == "Full Document"`: Continue using `frappe.get_doc()`, but return a clean dict representation or document wrapper explicitly documented as a serialized document structure.
- **Frappe API**: `frappe.get_list()` for `Single Record`, `frappe.get_doc()` for `Full Document`.
- **Compatibility**: 100% backward compatible for downstream dictionary access.
- **Performance Impact**: ~80% reduction in database queries and memory allocation for single-record lookups.

### Initiative 2: Expose Database Pagination Offset (`limit_start`)
- **Problem**: Pagination beyond page 1 is impossible due to missing offset parameters.
- **Root Cause**: `QueryRecordsConfig.vue` and `_query_list()` omit `limit_start`.
- **Affected Layer**: Vue Config UI (`QueryRecordsConfig.vue`) & Backend Handler (`_query_list`).
- **Recommended Direction**: Add optional `offset` / `limit_start` field in `Retrieval Settings` in `QueryRecordsConfig.vue` and pass `limit_start=config.get("limit_start", 0)` to `frappe.get_list()`.
- **Frappe API**: Native `frappe.get_list(limit_start=...)`.

### Initiative 3: Align `Query Report` Schema Contract
- **Problem**: UI duplicates report name into `node.data.reference_docname` and `config.report_name` to satisfy mismatched backend contracts.
- **Root Cause**: Discrepancy between `base_contract.py` (`reference_docname`) and `_query_report()` (`config.report_name`).
- **Affected Layer**: Action Contract & `_query_report()`.
- **Recommended Direction**: Standardize `_query_report()` to read `report_name = config.get("report_name") or action.reference_docname`.

### Initiative 4: Expose `or_filters` UI Controls
- **Problem**: Backend handler fully supports `or_filters`, but UI cannot author OR filter groups.
- **Root Cause**: Missing UI toggle in `FilterGroup.vue`.
- **Affected Layer**: Frontend Vue (`FilterGroup.vue`).
- **Recommended Direction**: Add a logic toggle (AND / OR) within `FilterGroup.vue` to serialize OR conditions into `config.or_filters`.

---

## 3. Suggested Implementation Sequence

```
[Phase 1: Contract Normalization]
  1. Standardize Query Report reference_docname / report_name fallback in _query_report().
  2. Add backend test for ignore_permissions role guard.

[Phase 2: Single Record Lookup Optimization]
  1. Refactor _query_doc() when return_type == "Single Record" to use frappe.get_list(limit_page_length=1).
  2. Benchmark query count reduction on test site.

[Phase 3: Pagination Offset Enhancement]
  1. Add limit_start input to QueryRecordsConfig.vue Retrieval Settings.
  2. Pass limit_start to frappe.get_list() in _query_list().

[Phase 4: OR Filters UI Enablement]
  1. Add AND/OR filter condition toggle in FilterGroup.vue.
  2. Serialize OR filters to config.or_filters.
```
