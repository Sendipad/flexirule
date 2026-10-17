# FlexiRule Query Records Canonical Query Schema Specification

## 1. Executive Overview & Schema Principles

This document defines the canonical declarative query schema for FlexiRule's `Query Records -> Fetch Records` operation. The schema establishes a versioned, metadata-validated contract that bridges FlexiRule's visual rule builder UI with Frappe Framework's native `frappe.qb.get_query()` engine.

### Key Schema Design Principles:
1. **Explicit Result Modes:** Result cardinality and structure are explicitly declared (`flat`, `nested`, or `aggregate`) rather than implicitly triggered by selected fields.
2. **Declarative Metadata Mapping:** Every field, 1-hop relationship, child table, alias, and function is represented declaratively and validated against active Frappe DocType metadata.
3. **100% Backward Compatibility:** Legacy Fetch Records configurations (`{ fields, filters, order_by, group_by, limit, offset, distinct }`) automatically normalize into Schema `version: "1.0"` with `result_mode: "flat"`, guaranteeing zero downtime and requiring no data migrations.
4. **Zero-N+1 Execution Guarantee:** Nested child document retrieval leverages Frappe's native `ChildQuery` batching mechanism ($O(1)$ query count), executing exactly 1 parent query and 1 query per child table.
5. **Strict Permission & Validation Boundaries:** Schema validation enforces hard safety guardrails (e.g., rejecting multi-hop link paths `a.b.c` and raw SQL/Python strings) before query construction.

---

## 2. Canonical Query Schema Specification (`version: "1.0"`)

The canonical schema is a serializable JSON object stored under `action.config` for Fetch Records action nodes.

### Schema Fields & Data Types

| Field Name | Type | Required | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| `version` | `string` | **Yes** | `"1.0"` | Schema version identifier for payload migration and compiler dispatch. |
| `source_doctype` | `string` | **Yes** | Fallback to `action.reference_doctype` | Primary target DocType name (e.g. `"Sales Invoice"`). |
| `result_mode` | `string` | **Yes** | `"flat"` | Target output shape: `"flat"` (joined rows), `"nested"` (parent dict with child arrays), or `"aggregate"` (grouped/aggregated result). |
| `fields` | `array[string]` | No | `["name"]` | Fields to select from primary table or 1-hop link fields (e.g. `["name", "customer.customer_name as cust_name"]`). |
| `children` | `array[object]` | Conditional | `[]` | Used in `nested` result mode. List of child table selections: `[{ "fieldname": "items", "fields": ["item_code", "qty", "rate"] }]`. |
| `functions` | `array[object]` | Conditional | `[]` | List of computed/aggregate function specifications: `[{ "function": "SUM", "field": "grand_total", "alias": "total_revenue" }]`. |
| `filters` | `object` | No | `{ "type": "group", "operator": "and", "children": [] }` | Canonical `QueryFilterTree` filter structure. |
| `order_by` | `array[object]` | No | `[]` | Ordered sort specifications: `[{ "field": "modified", "direction": "desc" }]`. |
| `group_by` | `array[string]` | Conditional | `[]` | Field paths to group by (e.g. `["customer", "posting_date"]`). Required when using aggregate functions in `aggregate` mode. |
| `distinct` | `boolean` | No | `false` | When `true`, applies `DISTINCT` row deduplication to parent query results. |
| `limit` | `integer \| string \| dict` | No | `null` | Maximum record count. Accepts static integers or dynamic expressions (e.g. `"{vars.max_limit}"` or FlexValue object). |
| `offset` | `integer \| string \| dict` | No | `null` | Record offset for pagination. Accepts static integers or dynamic expressions. |

---

## 3. Result Modes & Backend Execution Semantics

### 3.1 Mode A: `"flat"` (Joined Rows)
* **Semantics:** Queries the primary table and joins 1-hop Link DocTypes or Child Tables, producing a flat list of dictionaries (`list[dict]`).
* **Field Syntax:** Supports direct fields (`"name"`), 1-hop link fields (`"customer.customer_name"`), aliases (`"customer.customer_name as client_name"`), and flat child fields (`"items.item_code"`).
* **Cardinality Notice:** If a child field (e.g. `"items.item_code"`) is selected in `flat` mode, parent records will repeat for each child row, reflecting standard SQL join behavior.
* **Compiled `frappe.qb.get_query()` Call:**
  ```python
  frappe.qb.get_query(
      source_doctype,
      fields=["name", "customer.customer_name as client_name", "items.item_code"],
      filters=compiled_filters,
      order_by="modified desc",
      limit=20,
      distinct=False
  )
  ```

---

### 3.2 Mode B: `"nested"` (Parent Documents with Child Arrays)
* **Semantics:** Returns parent document dictionaries with child table records attached as nested list arrays under `row[child_fieldname]`.
* **Field Syntax:** `fields` declares parent and 1-hop link fields. `children` explicitly declares child table selections:
  ```json
  "children": [
    {
      "fieldname": "items",
      "fields": ["item_code", "qty", "rate", "amount"]
    }
  ]
  ```
* **Execution Strategy:**
  1. Compiles parent query: `frappe.qb.get_query("Sales Invoice", fields=["name", "customer", {"items": ["item_code", "qty", "rate", "amount"]}], ...)`
  2. `Engine.parse_fields()` instantiates `ChildQuery("items", [...], "Sales Invoice")`.
  3. Parent query executes first, fetching parent records.
  4. `execute_child_queries()` extracts `parent_names` and executes **1 batched SQL query**:
     `SELECT item_code, qty, rate, amount, parent, parentfield FROM tabSales Invoice Item WHERE parenttype='Sales Invoice' AND parentfield='items' AND parent IN (...) ORDER BY idx asc`
  5. Attaches matching child dicts under `row["items"]` for each parent object.
* **Output Shape:**
  ```json
  [
    {
      "name": "SINV-0001",
      "customer": "CUST-001",
      "items": [
        { "item_code": "ITEM-A", "qty": 2, "rate": 50, "amount": 100 },
        { "item_code": "ITEM-B", "qty": 1, "rate": 200, "amount": 200 }
      ]
    }
  ]
  ```

---

### 3.3 Mode C: `"aggregate"` (Grouped & Computed Results)
* **Semantics:** Computes aggregate function metrics (e.g. `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`) across filtered records, optionally grouped by specified fields.
* **Field Syntax:** Uses the `functions` array and `group_by` array:
  ```json
  "functions": [
    { "function": "COUNT", "field": "name", "alias": "total_invoices" },
    { "function": "SUM", "field": "grand_total", "alias": "total_revenue" }
  ],
  "group_by": ["customer"]
  ```
* **Compiled `frappe.qb.get_query()` Call:**
  ```python
  frappe.qb.get_query(
      source_doctype,
      fields=["customer", "COUNT(name) as total_invoices", "SUM(grand_total) as total_revenue"],
      filters=compiled_filters,
      group_by="customer"
  )
  ```

---

## 4. Normalization & Backward Compatibility Strategy

### Zero-Migration Normalization Pipeline

To guarantee complete backward compatibility for existing saved rules without database migrations, `QueryRecordsHandler` and `useActionConfig.js` will apply a transparent normalization pass during load/execution:

#### Input Payload (Legacy Configuration):
```json
{
  "fields": ["name", "status", "grand_total"],
  "filters": {
    "type": "group",
    "operator": "and",
    "children": [
      { "type": "leaf", "field": "status", "operator": "=", "value": "Submitted" }
    ]
  },
  "order_by": "modified desc",
  "limit": 50,
  "distinct": false
}
```

#### Normalized Canonical Payload (`version: "1.0"`):
```json
{
  "version": "1.0",
  "source_doctype": "Sales Invoice",
  "result_mode": "flat",
  "fields": ["name", "status", "grand_total"],
  "children": [],
  "functions": [],
  "filters": {
    "type": "group",
    "operator": "and",
    "children": [
      { "type": "leaf", "field": "status", "operator": "=", "value": "Submitted" }
    ]
  },
  "order_by": [{ "field": "modified", "direction": "desc" }],
  "group_by": [],
  "distinct": false,
  "limit": 50,
  "offset": null
}
```

### Normalization Logic Rules:
1. If `version` is missing, inject `"version": "1.0"`.
2. If `result_mode` is missing, default to `"flat"`.
3. If `fields` contains dicts (e.g. `{"items": [...]}`), automatically set `result_mode: "nested"` and extract into `children`.
4. String `order_by` (e.g. `"modified desc, name asc"`) is parsed into an array of sort objects.
5. Filter trees are validated to ensure they conform to the canonical `QueryFilterTree` format (`type: "group"` / `type: "leaf"`).

---

## 5. Downstream Consumer Contract Verification

Inspection of all downstream consumers in FlexiRule confirms complete compatibility with the Canonical Query Schema:

1. **Context Variable Storage:**
   Results produced by `flat`, `nested`, or `aggregate` modes are stored in `context.vars[return_variable]` using standard mutation modes (`Set Context Variable`, `Update Context Variable`, `Append to Context Variable`).

2. **Collection Resolvers (`family: "collection"`):**
   * `flat` & `nested` modes produce `list[dict]`, which Collection Resolvers (`count`, `sum`, `avg`, `filter`, `pluck`, `find`, `unique`) natively accept and operate upon.
   * For `nested` documents, Collection Resolvers can target child arrays via dotted paths (e.g. `vars.invoices[0].items`).

3. **Condition Nodes & Loop Nodes:**
   * Condition nodes checking `vars.invoices` evaluate record count or field equality seamlessly.
   * Loop nodes iterate over `vars.invoices` item-by-item, exposing child arrays like `loop.item.items` to inner rule flow actions.

---

## 6. Representative Canonical Schema Examples

### Example A: Nested Parent Document Query
```json
{
  "version": "1.0",
  "source_doctype": "Sales Invoice",
  "result_mode": "nested",
  "fields": ["name", "posting_date", "customer.customer_name as client_name"],
  "children": [
    {
      "fieldname": "items",
      "fields": ["item_code", "qty", "rate", "amount"]
    }
  ],
  "functions": [],
  "filters": {
    "type": "group",
    "operator": "and",
    "children": [
      {
        "type": "leaf",
        "field": "docstatus",
        "operator": "=",
        "value": 1
      },
      {
        "type": "leaf",
        "field": "posting_date",
        "operator": "timespan",
        "value": "this month"
      }
    ]
  },
  "order_by": [{ "field": "posting_date", "direction": "desc" }],
  "group_by": [],
  "distinct": false,
  "limit": 100,
  "offset": 0
}
```

### Example B: Grouped Aggregate Metric Query
```json
{
  "version": "1.0",
  "source_doctype": "Sales Invoice",
  "result_mode": "aggregate",
  "fields": ["customer"],
  "children": [],
  "functions": [
    { "function": "COUNT", "field": "name", "alias": "invoice_count" },
    { "function": "SUM", "field": "grand_total", "alias": "total_spent" }
  ],
  "filters": {
    "type": "group",
    "operator": "and",
    "children": [
      { "type": "leaf", "field": "docstatus", "operator": "=", "value": 1 }
    ]
  },
  "order_by": [{ "field": "total_spent", "direction": "desc" }],
  "group_by": ["customer"],
  "distinct": false,
  "limit": 10,
  "offset": 0
}
```

---

## 7. Phased Implementation & Testing Roadmap

Upon approval of this specification, implementation will proceed according to the following phased roadmap:

* **Phase 1 (Backend Compiler Refactoring):** Update `QueryRecordsHandler._fetch_records()` in `flexirule/ruleflow/core/action_handlers/query_records.py` to parse, normalize, and compile the Canonical Query Schema (`version: "1.0"`).
* **Phase 2 (UI Component Refactoring):** Expand `FetchRecordsConfig.vue` to introduce progressive step/tab navigation for Result Mode selection (`flat`, `nested`, `aggregate`), child table pickers, and function builders.
* **Phase 3 (Validation & Guardrails):** Implement server-side and client-side validation to reject multi-hop link paths (`a.b.c`), non-allowlisted SQL functions, and invalid result-mode field combinations.
* **Phase 4 (Automated Testing & Verification):** Add unit tests, integration tests against real DocTypes (`Sales Invoice`, `Customer`, `Sales Invoice Item`), and save/reload round-trip tests in `flexirule/ruleflow/tests/test_fetch_records.py`.
