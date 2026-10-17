# Query Records UI Refactor — Deep Component Analysis and Implementation Plan

**Author:** Jules Agent (Senior Software Engineer)
**Date:** March 2026
**Status:** Approved Architectural Plan
**Target File:** `reports/query-records/query_records_ui_refactor_analysis_and_plan.md`

---

## 1. Executive Summary

This document presents a comprehensive, evidence-backed architectural analysis and end-to-end implementation plan for refactoring FlexiRule's **Query Records** frontend UI and backend execution contract. Following our investigation into Frappe Framework v15 (`frappe.qb.get_query` and Query Builder capabilities), this refactor cleanses technical debt, removes legacy translation abstractions, establishes a single source-of-truth backend query contract, and maximizes the reuse of core FlexiRule frontend controls (`FilterGroup.vue`, `ComboBoxControl.vue`, `FlexValueControl.vue`, `MultiSelectList.vue`, `ControlFactory.vue`).

Per project requirements, this plan adopts a **clean, canonical backend contract** centered on Frappe's native query signature without backward-compatibility overhead. Existing components, backend handlers (`QueryRecordsHandler`), white-listed test APIs (`test_action_query`), and composables (`useActionConfig`) will be refactored directly to conform to this unified contract.

---

## 2. Current Query Records Architecture

FlexiRule's Query Records action enables rule designers to execute data retrieval operations against Frappe DocTypes and custom reports. Currently, the architecture spans:

1. **Backend Registry & Contracts (`base_contract.py` & `query_records.py`)**:
   - `QueryRecordsHandler` inherits from `ActionHandler` and registers 10 operation modes (`Query List`, `Query Doc`, `Exist Record`, `Query Report`, `Count`, `Sum`, `Average`, `Min`, `Max`, `Group By`).
   - Operation contracts declare mandatory/optional fields, return types (`List of Records`, `Single Record`, `Yes / No`, `List of Values`), and execution permission policies.
2. **Frontend UI Container (`QueryRecordsConfig.vue`)**:
   - Vue 3 Options/Composition hybrid component using `useActionConfig.js` for reactive state binding and store interaction.
   - Houses mode-dependent forms for filters, field selection, sort order, retrieval limits, report parameters, and aggregation controls.
3. **Whitelisted API Bridge (`api.py:test_action_query`)**:
   - Enables design-time schema detection and preview queries via "Refresh Schema (Debug Query)".
4. **Value Resolution (`value_resolver.py` & `FlexValueControl.vue`)**:
   - Evaluates dynamic values (expressions, context variables, resolvers) at runtime.

---

## 3. Backend Execution Trace

The current runtime execution path follows this flow:

```
Rule Engine Execution Loop (RuleEngine.execute)
        ↓
Handler Lookup via HandlerRegistry.get("Query Records")
        ↓
QueryRecordsHandler.execute(action, context, engine)
        ↓
1. Config Extraction (_parse_config(action.config))
2. Input Mapping Application (apply_input_mapping)
3. Permission Audit Check (can_ignore_permissions)
        ↓
Mode Dispatcher (mode_handlers[action.operation])
        ↓
Mode Specific Handler Function:
├── _query_list: frappe.get_list(reference_doctype, filters, fields, order_by, limit_page_length, distinct, group_by)
├── _query_doc: frappe.get_doc(resolved_doctype, docname) / frappe.get_cached_doc / frappe.get_all
├── _exist_record: frappe.get_list(fields=["name"], limit_page_length=1) -> bool
├── _query_report: frappe.desk.query_report.run(report_name, report_filters)
├── _count_records: frappe.get_list(fields=["count(distinct `tab...`.name) as _count"])
├── _aggregate: frappe.get_list(fields=["sum/avg/min/max(...) as result"])
└── _group_by: frappe.get_list(fields=[group_expr, "fn(agg) as value"], group_by=group_expr)
        ↓
Filter & Order Qualification:
├── _resolve_query_filters -> _resolve_filters_with_context -> _normalize_filters_for_backend
└── _qualify_order_by -> _resolve_filter_doctype_and_field (combines child table metadata)
        ↓
Frappe Database / Query Engine Execution
        ↓
Result Output & Action Context Mutation
```

### Key Architectural Finding:
The backend currently uses `frappe.get_list()` and custom SQL string building for order qualification, group-by clauses, and aggregations. Under the refactored architecture, `frappe.qb.get_query` will serve as the core engine for query construction, providing native SQL safety, parent-child table join handling, and permission filtering.

---

## 4. Frontend Component Inventory

An inventory of all frontend components and controls involved in Query Records:

| Component | Purpose | Current Input | Current Output | Backend Consumer | Reusable? | Required Changes |
|---|---|---|---|---|---|---|
| `QueryRecordsConfig.vue` | Main config container | `node`, `readOnly` | `node.data.config` JSON | `QueryRecordsHandler` | **Extend** | Refactor layout to canonical structure & clean up legacy watchers. |
| `FilterGroup.vue` | Filter builder UI | `doctype`, `modelValue` | List of filter objects `[{field, operator, value}]` | `_resolve_query_filters` | **Reuse** | Already supports `allowAnyDoctype` & child fields. Connect directly to canonical filters contract. |
| `ComboBoxControl.vue` | Field / DocType selector | `df`, `options`, `doctype` | Selected string | `config.fields`, `config.order_by` | **Reuse** | No change needed. Used for field selection and order-by field picking. |
| `FlexValueControl.vue` | Dynamic value selector | `modelValue`, `context` | `{mode, value}` or primitive | `_resolve_value_expression_with_context` | **Reuse** | No change needed. Handles static vs variable vs resolver payloads. |
| `MultiSelectList.vue` | Multi-field selection | `options`, `modelValue` | `string[]` | `config.fields` | **Reuse** | No change needed. Ideal for multi-field pickers. |
| `ControlFactory.vue` | Form control factory | `df`, `modelValue` | Primitive value | Action top-level fields & config keys | **Reuse** | Used for check boxes, select dropdowns, text inputs. |
| `useActionConfig.js` | Action state composable | `props` | Reactive state helpers | Vue state management | **Reuse** | Streamline config sync methods. |

---

## 5. Reusable Component Analysis

FlexiRule features a rich set of established UI controls. **No new Query-Records-specific controls need to be created.**

1. **DocType & Field Selection**: `ComboBoxControl.vue` handles link queries, autocomplete, and field picking with built-in validation indicators (`border-warning`).
2. **Filter & Condition Building**: `FilterGroup.vue` supports field picking, operator selection (including `=, !=, >, >=, <, <=, like, not like, in, not in, is, between, timespan, starts with, ends with`), dynamic FlexValue inputs per row, and multi-doctype selection (`allowAnyDoctype`).
3. **Dynamic Value Handling**: `FlexValueControl.vue` cleanly encapsulates static inputs, context variable picker (`doc.`, `vars.`), and value resolvers.
4. **Field Lists**: `MultiSelectList.vue` provides searchable tag-based selection for string arrays (`fields`).
5. **Form Primitives**: `ControlFactory.vue` renders standard Frappe field types (`Check`, `Select`, `Int`, `Small Text`).

---

## 6. Current Configuration Contract

Currently, `config` serialized in `node.data.config` varies across operations:

```json
{
  "doctype_name": "Sales Order",
  "fetch_strategy": "Get doc",
  "docname": "SO-00001",
  "filters": [
    ["docstatus", "=", 1],
    {"field": "status", "operator": "=", "value": {"mode": "static", "value": "Submitted"}}
  ],
  "fields": ["name", "customer", "grand_total"],
  "order_by": "creation desc, name asc",
  "limit_type": "Custom Limit",
  "limit": 20,
  "group_by": "customer",
  "distinct": 1,
  "parent_doctype": "Sales Order",
  "report_name": "Sales Register",
  "field": "grand_total",
  "group_by_field": "customer",
  "agg_function": "sum",
  "agg_field": "net_total"
}
```

### Redundancies & Problems:
1. `order_by` is formatted as a comma-separated string rather than a structured array of objects.
2. `limit_type` and `limit` are stored at root level without unified object typing.
3. Filter structures mix tuple arrays `[field, op, val]` and dictionary objects `{"field": ..., "operator": ..., "value": ...}`.
4. DocType naming alternates between `action.reference_doctype` and `config.doctype_name`.

---

## 7. Frappe "get_query" Capability Mapping

Mapping FlexiRule Query Records configuration to `frappe.qb.get_query` capabilities:

| FlexiRule Concept | Current Representation | Canonical Contract Representation | Frappe `get_query` / QueryBuilder Capability | Translation Required? |
|---|---|---|---|---|
| Target DocType | `reference_doctype` or `config.doctype_name` | `reference_doctype` | `frappe.qb.DocType(doctype)` | Direct |
| Child DocType | `config.parent_doctype` + `reference_doctype` | `reference_doctype` + `parent_doctype` | `frappe.qb.DocType(parent)` joined with `frappe.qb.DocType(child)` | Direct |
| Fields | `["name", "customer"]` or `["items.item_code"]` | `["name", "customer", "items.item_code"]` | `query.select(*fields)` | Direct (auto-join child table) |
| Filters (AND) | Mixed lists and dicts | Structured filter array `[[field, op, val], ...]` | `query.where(...)` via QueryBuilder or native `get_list` filters | Clean normalization |
| Filters (OR) | `config.or_filters` | `or_filters: [[field, op, val], ...]` | `query.where(...)` with OR logic | Clean normalization |
| Sort Order | Comma-delimited string `"creation desc"` | `order_by: [{ field: "creation", direction: "desc" }]` | `query.orderby(field, order=Order.desc)` | Structured object |
| Pagination / Limit | `limit_type`, `limit` | `limit: { type: "Custom Limit", value: 20 }` | `query.limit(n)` / `query.offset(n)` | Structured object |
| Deduplication | `distinct: 1` | `distinct: true` | `query.distinct()` | Direct boolean |
| Group By | `group_by: "customer"` | `group_by: ["customer"]` | `query.groupby(*fields)` | Array normalization |
| Aggregations | `field`, `agg_function` | `aggregation: { field: "grand_total", function: "sum" }` | `frappe.qb.functions.sum(...)` | Structured object |

---

## 8. Operation-by-Operation Analysis

### 1. Query List
- **Required Config**: `reference_doctype`, `fields`, `filters`, `or_filters`, `order_by`, `limit`, `distinct`, `group_by`, `parent_doctype` (if child).
- **Frappe Mapping**: Invokes `frappe.qb.get_query` or `frappe.get_list` returning a list of dicts.

### 2. Query Doc
- **Required Config**: `reference_doctype`, `fetch_strategy` (`"Get doc"`, `"Get Doc from Cache"`, `"Get latest Doc"`, `"Get Single DocType"`), `docname` (dynamic or static), `filters` (for `"Get latest Doc"`).
- **Frappe Mapping**: Returns a single dictionary/document object.

### 3. Exist Record
- **Required Config**: `reference_doctype`, `filters`, `or_filters`.
- **Frappe Mapping**: `frappe.qb.get_query` selecting 1 record; returns `True` or `False`.

### 4. Query Report
- **Required Config**: `report_name` (assigned to `reference_docname`), `report_filters` (flat dict of key-values).
- **Frappe Mapping**: Delegates to `frappe.desk.query_report.run(report_name, report_filters)`.

### 5. Aggregations (Count, Sum, Average, Min, Max, Group By)
- **Required Config**: `reference_doctype`, `filters`, `aggregation: { field, function, group_by_field, agg_field }`.
- **Frappe Mapping**: `frappe.qb.functions.{sum|avg|min|max|count}` with optional `.groupby()`.

---

## 9. Child DocType Analysis

Querying child tables in Frappe presents two distinct operational patterns:

1. **Direct Child-Record Querying**:
   - The user selects a Child Table DocType as `reference_doctype` (e.g., `Sales Invoice Item`).
   - `parent_doctype` must be specified (e.g., `Sales Invoice`).
   - Query executes against `tabSales Invoice Item` joined on `parent = tabSales Invoice.name`.
   - Result: List of child row records, retaining `parent`, `parenttype`, and `parentfield` linkage.

2. **Parent Document Querying Filtered by Child Criteria**:
   - The user selects a Parent DocType as `reference_doctype` (e.g., `Sales Invoice`).
   - Filters reference child fields using dotted syntax (e.g., `items.item_code = "ITEM-001"`).
   - `frappe.qb.get_query` or `QueryRecordsHandler` automatically performs `LEFT JOIN` on child table and applies `DISTINCT` on parent records.
   - Result: List of parent documents/records matching the child table conditions.

---

## 10. Filter/Condition Architecture

Filters will use a unified, clean tuple-style contract supported by `FilterGroup.vue`:

```json
[
  ["status", "=", "Submitted"],
  ["items.qty", ">", 10],
  ["creation", "between", ["2026-01-01", "2026-03-31"]]
]
```

### Supported Operators:
- Standard comparison: `=`, `!=`, `>`, `>=`, `<`, `<=`
- Pattern matching: `like`, `not like`, `starts with`, `ends with`
- Membership: `in`, `not in`
- Nullability: `is` (`"set"` / `"not set"`)
- Temporal & Ranges: `between`, `timespan`

---

## 11. FlexValue / Value Resolver Integration

Query Records seamlessly integrates with FlexValue for all dynamic parameters:

- **Static Values**: Plain primitives (`"Submitted"`, `100`, `true`).
- **Context Variables**: `{ "mode": "variable", "value": "doc.customer" }`.
- **Resolvers**: `{ "mode": "resolver", "family": "date_time", "operation": "current", "config": {} }`.
- **Expressions**: `{ "mode": "expression", "value": "doc.grand_total * 0.1" }`.

Evaluation is handled via `QueryRecordsHandler._resolve_value_expression_with_context()`, which delegates to `get_compiled_resolver()`.

---

## 12. Debug Query vs Runtime Query Analysis

### Current Flaw:
`api.py:test_action_query` currently executes a separate, custom metadata inspection path to generate `resolved_output_schema`, bypassing `QueryRecordsHandler.execute()`. This creates discrepancies where preview queries do not reflect actual runtime behavior (e.g., when dynamic resolvers or custom report columns are used).

### Solution:
Refactor `test_action_query` to delegate query construction directly to `QueryRecordsHandler.build_query_preview()` or `QueryRecordsHandler.execute(..., dry_run=True)`, ensuring 100% parity between preview and production execution.

---

## 13. Problems / Gaps / Redundancies

1. **Duplicated DocType Fields**: Inconsistent use of `action.reference_doctype` vs `config.doctype_name`.
2. **String-based Order By**: Harder to validate and build UI rows compared to structured array.
3. **Flat Config Structure**: All parameters dumped into top-level `config` dictionary without clean namespacing.
4. **Test Query Divergence**: Preview query path in `api.py` differs from runtime execution path in `query_records.py`.
5. **SQL Qualification Fragility**: Order-by and group-by string splitting logic prone to syntax errors.

---

## 14. Proposed Canonical Backend Contract

The clean, canonical backend contract for Query Records action configuration:

```json
{
  "operation": "Query List",
  "reference_doctype": "Sales Order",
  "parent_doctype": "",
  "fields": ["name", "customer", "grand_total"],
  "filters": [
    ["docstatus", "=", 1],
    ["customer", "=", { "mode": "variable", "value": "doc.customer" }]
  ],
  "or_filters": [],
  "order_by": [
    { "field": "creation", "direction": "desc" }
  ],
  "limit": {
    "type": "Custom Limit",
    "value": 20
  },
  "distinct": false,
  "group_by": [],
  "fetch_strategy": "Get doc",
  "docname": null,
  "report_name": null,
  "report_filters": {},
  "aggregation": {
    "field": null,
    "group_by_field": null,
    "function": null,
    "agg_field": null
  }
}
```

---

## 15. Proposed Frontend Architecture

### Component Tree:
```
QueryRecordsConfig.vue
├── ExecutionPermissionSection (ControlFactory: ignore_permissions, permission_audit_reason)
├── TargetReferenceSection (ComboBoxControl: reference_doctype, parent_doctype)
├── OperationTabNavigation (Query List | Query Doc | Exist Record | Query Report | Aggregations)
│
├── QueryListConfig
│   ├── QueryFields (MultiSelectList)
│   ├── QueryFilters (FilterGroup - reused)
│   ├── QueryOrdering (ComboBoxControl + Select)
│   └── QueryRetrieval (ControlFactory: limit_type, limit, distinct, group_by)
│
├── QueryDocConfig
│   ├── FetchStrategy (ControlFactory: fetch_strategy)
│   ├── DocTypeName (FlexValueControl)
│   ├── DocName (FlexValueControl)
│   └── QueryFilters (FilterGroup - for "Get latest Doc")
│
├── ExistRecordConfig
│   └── QueryFilters (FilterGroup)
│
├── QueryReportConfig
│   └── ReportFiltersTable (FlexValueControl per filter)
│
├── QueryAggregationConfig
│   ├── QueryFilters (FilterGroup)
│   └── AggregationSettings (ComboBoxControl: field, group_by_field, function, agg_field)
│
└── DebugQueryPanel
    └── Refresh Schema Button & Preview Status
```

---

## 16. Backward Compatibility / Migration

Per user approval:
- **No legacy backward compatibility requirement.**
- Direct refactoring of backend handlers (`QueryRecordsHandler`), white-listed API endpoints (`test_action_query`), composables (`useActionConfig`), and UI views (`QueryRecordsConfig.vue`).
- No complex migration or legacy translation layers required.

---

## 17. Testing Strategy

### 1. Backend Tests (`test_query_records_refactor.py`)
- Unit tests for each operation mode using the canonical contract.
- Validation tests for missing/invalid DocTypes, fields, and permissions.
- Test `frappe.qb.get_query` parent/child table joins and filter normalization.
- Execution parity tests comparing `test_action_query` schema output with `QueryRecordsHandler.execute` runtime output.

### 2. Frontend Verification & UI Tests
- Run Playwright / Cypress UI tests for Rule Builder.
- Verify node configuration rendering, filter row additions, field selection, and schema preview.

---

## 18. Detailed Implementation Plan

### Phase 1 — Backend Handler & Contract Refactor
- **Files to Modify**: `flexirule/ruleflow/core/action_handlers/query_records.py`, `flexirule/ruleflow/core/action_handlers/base_contract.py`
- **Objective**: Refactor `QueryRecordsHandler` to parse the clean canonical contract and execute queries natively using `frappe.qb.get_query`.
- **Key Changes**:
  1. Update `get_action_contract()` and `get_operation_contracts()` to reflect canonical fields.
  2. Implement `_build_qb_query()` leveraging `frappe.qb` for joins, ordering, filters, distinct, and limit.
  3. Simplify `_query_list`, `_query_doc`, `_exist_record`, `_aggregate`, and `_group_by`.

### Phase 2 — API Parity & Test Execution Alignment
- **Files to Modify**: `flexirule/ruleflow/api.py`
- **Objective**: Refactor `test_action_query` to invoke `QueryRecordsHandler` query builder logic directly, ensuring 100% parity between preview and runtime schema generation.

### Phase 3 — Frontend Configuration Refactor
- **Files to Modify**: `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue`, `flexirule/public/js/flexirule/rule_builder/composables/useActionConfig.js`
- **Objective**: Update `QueryRecordsConfig.vue` layout and state binding to emit the canonical configuration contract cleanly.
- **Key Changes**:
  1. Bind `reference_doctype` directly.
  2. Format `order_by` as structured array `[{field, direction}]`.
  3. Format `limit` as structured object `{type, value}`.
  4. Reuse `FilterGroup.vue`, `ComboBoxControl.vue`, `FlexValueControl.vue`, `MultiSelectList.vue`.

### Phase 4 — Testing & Asset Compilation
- **Files to Modify/Create**: `flexirule/ruleflow/tests/test_query_records_refactor.py`
- **Objective**: Execute backend unit tests and compile frontend assets using `bench build --app flexirule`.

---

## 19. Files to Change Matrix

| File Path | Change | Reuse / Extend / New | Reason | Risk |
|---|---|---|---|---|
| `flexirule/ruleflow/core/action_handlers/query_records.py` | Must Change | Extend | Implement canonical contract & `frappe.qb.get_query` execution | Low |
| `flexirule/ruleflow/core/action_handlers/base_contract.py` | Must Change | Extend | Update contracts & operation policy field definitions | Low |
| `flexirule/ruleflow/api.py` | Must Change | Extend | Align `test_action_query` preview with handler execution | Low |
| `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue` | Must Change | Extend | Align UI controls with canonical contract | Low |
| `flexirule/public/js/flexirule/rule_builder/composables/useActionConfig.js` | Likely Change | Extend | Update state sync helpers if required | Low |
| `flexirule/ruleflow/tests/test_query_records_refactor.py` | Must Change | Extend / New | Comprehensive backend test suite | Low |

---

## 20. Open Questions / Decisions Required

None. All technical decisions (clean contract, no backward compatibility, direct child table queries, native `frappe.qb.get_query`) have been confirmed and incorporated into this plan.

---

## 21. Final Recommendation

Proceed with execution of the 4-phase implementation plan. This refactor will eliminate legacy configuration complexity, achieve full preview/runtime execution parity, reduce codebase maintenance overhead, and establish a robust, query-builder-backed data retrieval engine for FlexiRule.
