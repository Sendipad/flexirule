# Fetch Records Architecture Review & Capability Assessment Report

**Repository:** `Sendipad/flexirule`
**Base Branch:** `feat/fetch-records-mode`
**Target Environment:** Frappe v15 (v15.121.1)

---

## 1. Executive Summary

This report establishes the baseline architectural review and Frappe v15 capability assessment for **Fetch Records** under the `Query Records` action type.

Previous experimental approaches attempted to parse raw string SQL function expressions through `frappe.qb.get_query()`, which failed due to limitations in Frappe's naive `get_function_object()` parser (e.g. missing `CONCAT`, `NOW`, or improper literal handling for `IFNULL`).

By adopting a **Structured Semantic Configuration Schema**, the backend compiles user intent directly into native PyPika / `frappe.query_builder.functions` terms and native Frappe query structures. This eliminates SQL injection risks, ensures robust execution across all database backends (MariaDB / PostgreSQL), and cleanly powers all four required result modes.

---

## 2. Frappe v15 Query Builder Capability Matrix

| Capability | Frappe Syntax / Term | Real Frappe v15 Behavior | Result Shape | UI Exposure | Backend Validation & Safety |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mode A: Doc Names** | `fields=['name']` | Minimized SQL `SELECT name FROM tabDocType` | `[{"name": "SO-00001"}]` | Default mode; hides field/function controls | Validated reference DocType |
| **Mode B: Whole Doc** | `fields=['name']` + `frappe.get_doc()` | Fetches matching names, loads complete docs with embedded child records | `[{"name": "SO-00001", "items": [...]}]` | Mode B option; hides field selection | Checks read permissions on loaded docs |
| **Mode C: Flat Fields** | `fields=['name', 'customer.customer_name', 'items.item_code']` | Performs left joins for Link fields and Child Tables. Row cardinality increases for child joins. | `[{"name": "SO-00001", "customer_name": "Cust A", "item_code": "ITEM-1"}]` | Flat field picker + function editor | Validates field paths against Meta |
| **Mode D: Embedded Child** | `fields=['name', 'customer', {'items': ['item_code', 'qty']}]` | Native 2-query child table batching (`ChildQuery` via `execute_child_queries`) | `[{"name": "SO-00001", "items": [{"item_code": "ITEM-1", "qty": 2}]}]` | Nested child section editor | Validates child field exists and is a Table field |
| **Aggregates** | `fn.Count`, `fn.Sum`, `fn.Avg`, `fn.Min`, `fn.Max` | Compiles to PyPika aggregate functions | `{ "total_qty": 15.0 }` | Structured function editor | Requires numeric fields for SUM/AVG; validates alias |
| **Scalar Functions** | `fn.Abs`, `fn.IfNull`, `fn.Concat`, `fn.Extract`, `fn.Now` | Compiles to PyPika / Frappe function terms | `{ "full_name": "John Doe" }` | Structured function editor | Validates required argument count and field types |
| **Order By** | `order_by="creation desc"` | PyPika `ORDER BY` with field qualification | Preserves record order | Sorting rows table editor | Qualifies fields (`tabDocType.field`) to prevent join ambiguity |
| **Pagination** | `limit=20`, `offset=0` | PyPika `.limit().offset()` | Page-bounded list | Retrieval settings grid | Integer validation; non-negative |
| **Deduplication** | `distinct=True` | PyPika `.distinct()` | Deduplicated row list | Checkbox control | Validates boolean |

---

## 3. Four Result Modes Specification

### Mode A — List of Document Names (`names`)
- **Contract:** Returns a list of dictionaries with document `name` values, e.g. `[{"name": "SO-00001"}, {"name": "SO-00002"}]`.
- **UI Behavior:** Default mode. Hides ordinary field selection, function expressions, and embedded child table controls. Retains filters, order_by, limit, offset, and distinct controls.
- **Backend Execution:** Minimal `frappe.qb.get_query(doctype, fields=['name'], ...)` execution.

### Mode B — Whole Documents (`whole_doc`)
- **Contract:** Returns complete parent documents including all child table arrays as dictionary objects.
- **UI Behavior:** Hides field selection and function controls. Retains filters, order_by, limit, offset.
- **Backend Execution:** Executes name query to gather matching document names, then loads each document using `frappe.get_doc(doctype, name).as_dict()`, enforcing read permissions per document.

### Mode C — Selected Fields (Flat) (`flat_fields`)
- **Contract:** Returns flat dictionaries containing selected parent fields, linked fields (`link.field`), flat child fields (`child.field`), and SQL function results with aliases.
- **UI Behavior:** Provides navigable field picker for parent and linked DocTypes, flat child field selection, and structured SQL function builder with mandatory alias definition.
- **Backend Execution:** Compiles parent fields, dynamic link/child table joins, and PyPika function terms into `frappe.qb.get_query()`.

### Mode D — Selected Fields with Embedded Child Records (`embedded_child`)
- **Contract:** Returns parent fields alongside nested arrays of child table records under the child table field key.
  ```json
  [
    {
      "name": "SO-00001",
      "customer": "Customer A",
      "items": [
        { "item_code": "ITEM-001", "qty": 2 }
      ]
    }
  ]
  ```
- **UI Behavior:** Selected parent fields section + dedicated nested editor for child table selection (`child_table` name + selected child fields).
- **Backend Execution:** Passes structured dictionary specs (e.g. `fields=['name', 'customer', {'items': ['item_code', 'qty']}]`) to `frappe.qb.get_query()`, utilizing Frappe's native `ChildQuery` batch query mechanism.

---

## 4. Semantic Configuration Schema Contract

Saved action configuration for `Fetch Records` strictly adheres to the following structured JSON schema (`config`):

```json
{
  "result_mode": "names",
  "fields": ["name", "customer_name", "customer.territory"],
  "functions": [
    {
      "function": "SUM",
      "args": [{ "type": "field", "value": "grand_total" }],
      "alias": "total_sales"
    },
    {
      "function": "CONCAT",
      "args": [
        { "type": "field", "value": "first_name" },
        { "type": "literal", "value": " " },
        { "type": "field", "value": "last_name" }
      ],
      "alias": "full_name"
    }
  ],
  "embedded_children": [
    {
      "child_field": "items",
      "fields": ["item_code", "qty", "rate", "amount"]
    }
  ],
  "filters": {
    "type": "group",
    "operator": "and",
    "children": [
      {
        "type": "leaf",
        "field": "docstatus",
        "operator": "=",
        "value": 1
      }
    ]
  },
  "order_by": "creation desc",
  "group_by": "customer",
  "limit": 20,
  "offset": 0,
  "distinct": false
}
```

---

## 5. Downstream Consumption Audit

When `QueryRecordsHandler.execute()` executes:
1. It dispatches to `_fetch_records(reference_doctype, config, context, action, ignore_permissions)`.
2. The handler executes the query and returns a `list[dict]` (or list of documents/dicts).
3. `RuleEngine._post_process_action_result()` receives the return value (`result`).
4. `ContextManager.apply_mutation()` applies `mutation_mode` (e.g., `"Set Context Variable"`), placing the `list[dict]` directly into `context["vars"][return_variable]`.
5. Later rule actions (e.g., Loop, Switch, Assignment, Process) reference `context["vars"][return_variable]` using standard FlexiValue expressions (e.g., `vars.my_records`, `row.item_code`).

All 4 result modes return clean list of dictionaries compatible with ContextManager variable resolution and path trace output logging.
