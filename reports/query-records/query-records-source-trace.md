# FlexiRule "Query Records" End-to-End Source Code Trace

## 1. Overview of Execution Layers

The "Query Records" action in FlexiRule transitions through 8 distinct layers from authoring in the Rule Builder UI to SQL execution and context variable mutation.

```
[Vue UI Configuration Component]
 (QueryRecordsConfig.vue)
        ↓
[JSON Serialization]
 (node.data.config string in Rule DocType / Graph payload)
        ↓
[Rule Engine Action Dispatch]
 (engine.py / RuleEngine.execute_action())
        ↓
[Handler Lookup & Pre-Validation]
 (HandlerRegistry -> QueryRecordsHandler.execute())
        ↓
[Permission & Audit Guard]
 (can_ignore_permissions())
        ↓
[Filter Resolution & Value Interpolation]
 (_resolve_query_filters() -> FlexValueControl / resolver)
        ↓
[Frappe API Invocation]
 (frappe.get_list / frappe.get_doc / query_report.run)
        ↓
[Result Context Mutation]
 (Context variable mutation -> return next_action)
```

---

## 2. Layer-by-Layer Detailed Trace

### Layer 1: Action Configuration & Contract Registration
- **Backend Contract**: `flexirule/ruleflow/core/action_handlers/query_records.py` (`get_action_contract()` & `get_operation_contracts()`)
- **Frontend Registry**: `flexirule/public/js/flexirule/core/contracts.js`
- **DocType Schema**: `flexirule/ruleflow/doctype/rule_action/rule_action.json`
- **Supported Operations**: `Query List`, `Query Doc`, `Exist Record`, `Query Report`, `Count`, `Sum`, `Average`, `Min`, `Max`, `Group By`.

### Layer 2: Frontend Vue Configuration Component
- **File**: `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue`
- **Role**: Renders mode-specific configuration cards:
  - **Query List**: `FilterGroup`, `MultiSelectList` (fields), `order_by_rows` (sort picker), `limit_type` & `limit` controls, `group_by` autocomplete, `distinct` checkbox.
  - **Query Doc**: `fetch_strategy` select, `doctype_name` (FlexValueControl), `docname` (FlexValueControl), conditional `FilterGroup` (for "Get latest Doc").
  - **Query Report**: `Report Name` picker, dynamic report filters form.
  - **Permission Section**: `ignore_permissions` checkbox & `permission_audit_reason` text input.
- **Serialization**: `sync_local_config()` serializes Vue reactive state into `node.data.config` as a JSON string.

### Layer 3: Serialized Action Payload Structure
When saved, the node data on the Rule document is stored as:
```json
{
  "action_type": "Query Records",
  "operation": "Query List",
  "reference_doctype": "Sales Order",
  "ignore_permissions": 1,
  "permission_audit_reason": "Automated background rule evaluation",
  "config": "{\"filters\":[[\"status\",\"=\",\"Submitted\"]],\"fields\":[\"name\",\"customer\",\"grand_total\"],\"order_by\":\"grand_total desc\",\"limit_type\":\"Custom Limit\",\"limit\":50}"
}
```

### Layer 4: Backend Engine Dispatch
- **File**: `flexirule/ruleflow/core/engine.py`
- **Method**: `RuleEngine.execute_action(action, context)`
- **Dispatch**: Searches `HandlerRegistry.get("Query Records")` and invokes `QueryRecordsHandler().execute(action, context, engine)`.

### Layer 5: Handler Execution & Permission Verification
- **File**: `flexirule/ruleflow/core/action_handlers/query_records.py`
- **Method**: `QueryRecordsHandler.execute(action, context, engine)`
- **Trace**:
  1. Parses JSON config: `config = self._parse_config(action.config)`.
  2. Evaluates permission bypass: `ignore_permissions = can_ignore_permissions(action, context, throw=True)`.
  3. Dispatches to internal mode handler dictionary:
     - `"Query List"` -> `self._query_list`
     - `"Query Doc"` -> `self._query_doc`
     - `"Exist Record"` -> `self._exist_record`
     - `"Query Report"` -> `self._query_report`
     - `"Count"` -> `self._count_records`
     - `"Sum"` / `"Average"` / `"Min"` / `"Max"` -> `self._aggregate`
     - `"Group By"` -> `self._group_by`

### Layer 6: Filter Resolution & Value Interpolation
- **Method**: `_resolve_query_filters(config, context, action, reference_doctype)`
- **Trace**:
  - Interpolates dynamic expression templates (e.g., `{doc.customer}` or FlexValueControl mode dicts) via `_resolve_value_expression_with_context()`.
  - Resolves child table dot-notation fields (`accounts.account`) to actual child DocType names via `_resolve_filter_doctype_and_field()`.
  - Normalizes filter items into standard list-of-lists format: `[["doctype", "field", "operator", "value"], ...]`.

### Layer 7: Frappe API Invocation & Database Query
- **`_query_list()`**:
  - Qualifies `order_by`: `order_by = self._qualify_order_by(reference_doctype, order_by)`.
  - Translates `limit_type` to `limit_page_length` (`All` -> `0`, `First Record` -> `1`, `Custom Limit` -> `int`).
  - Executes `frappe.get_list(reference_doctype, filters=filters, fields=fields, limit_page_length=limit, order_by=order_by, ignore_permissions=ignore_permissions, ...)`.
- **`_query_doc()`**:
  - Resolves target `docname` and `resolved_doctype`.
  - Executes `frappe.get_cached_doc(...)` or `frappe.get_doc(...)`.
  - Runs permission check `doc.check_permission("read")` if `ignore_permissions` is False.
  - Converts and returns `doc.as_dict()`.

### Layer 8: Action Output & Downstream Mutation
- **Return Value**: `result, next_action` is returned from `execute()`.
- **Engine Processing**: `RuleEngine` stores `result` into `context` according to `mutation_mode` (e.g., `Set Context Variable`, `Update Context Variable`) and advances execution to `next_action`.

---

## 3. Schema & Mapping Summary Table

| Operational Mode | Primary Inputs | Backend Method | Frappe API Called | Output Data Shape |
| :--- | :--- | :--- | :--- | :--- |
| **Query List** | `filters`, `fields`, `order_by`, `limit_type`, `limit`, `group_by`, `distinct` | `_query_list()` | `frappe.get_list()` | `list[frappe._dict]` |
| **Query Doc** | `fetch_strategy`, `doctype_name`, `docname`, `filters` | `_query_doc()` | `frappe.get_doc()` / `frappe.get_all()` | `frappe._dict` or `None` |
| **Exist Record** | `filters` | `_exist_record()` | `frappe.get_list()` | `bool` |
| **Query Report** | `report_name`, `filters` | `_query_report()` | `frappe.desk.query_report.run()` | `dict{"columns": [...], "result": [...]}` |
| **Count** | `filters` | `_count_records()` | `frappe.get_list()` | `int` |
| **Sum / Avg / Min / Max** | `field`, `filters` | `_aggregate()` | `frappe.get_list()` | `int` / `float` |
| **Group By** | `field`, `group_by_field`, `agg_function`, `filters` | `_group_by()` | `frappe.get_list()` | `list[frappe._dict]` |
