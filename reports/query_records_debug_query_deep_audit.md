# Deep Audit Report: Query Records — “Refresh Schema (Debug Query)”

**Date:** July 2025
**Target Application:** FlexiRule (Frappe App)
**Target Component:** Query Records Action Configuration (`QueryRecordsConfig.vue`) & Debug Query Backend API (`flexirule.ruleflow.api.test_action_query`)
**Frappe Framework Version:** v15+ (`frappe` 15.x / Python 3.12 / Node.js)
**Primary Deliverable File:** `reports/query_records_debug_query_deep_audit.md`

---

## Executive Summary

This deep audit report presents a source-backed, evidence-classified analysis of FlexiRule's **“Refresh Schema (Debug Query)”** capability for the **Query Records** action type.

The audit investigates the exact client-side triggers, API contracts, backend handlers, schema derivation logic, permission enforcement, dynamic resolver interactions, child table handling, and failure modes by directly examining the FlexiRule repository and comparing the **Debug Query path** against the **Runtime Query Records execution path**.

### Key Audit Findings

1. **Dual Schema Derivation Architecture (FACT):**
   - FlexiRule currently operates a hybrid dual-path schema mechanism:
     1. **Client-side Local Projection (`update_resolved_schema_local`):** Instantly parses DocType metadata (`frappe.utils.get_doctype_meta`) to build field schemas for basic selected fields.
     2. **Server-side RPC Query (`test_action_query`):** Invoked via the button `test_query` or debounced background watch `debounced_schema_update`.
2. **Intent & Meaning of "Schema" (INFERENCE / RECOMMENDATION):**
   - The label “Refresh Schema (Debug Query)” was intended to test/evaluate the configured Query Records action and return the **Runtime Result Schema** (i.e. the structured list of fields, labels, fieldtypes, and child properties that will actually be returned when downstream nodes consume this action's output variable).
   - However, `test_action_query` in `api.py` attempts a full execution of the action handler while simultaneously attempting static metadata schema extraction.
3. **Primary Root Cause of Failures (FACT):**
   - The primary reasons Debug Query fails or produces stale/empty schemas stem from **3 major architectural divergences**:
     - **Context Starvation for Dynamic Resolvers:** `test_action_query` initializes an empty context (`doc = frappe.get_doc(recent[0])` or `None`). When filters or fields use dynamic expressions (`doc.customer`, `vars.total`), `test_action_query` fails during evaluation or substitutes unresolved values with empty strings, causing SQL syntax errors or empty result sets.
     - **Pre-detection vs Result Inspection Coupling:** In `api.py:test_action_query`, `Query Report` schema detection is performed *after* report execution. If report execution fails (e.g. missing mandatory report filters), the function throws an exception before schema extraction completes, returning no schema at all.
     - **Configuration Loss:** Options like `distinct`, `group_by`, `parent_doctype`, `fetch_strategy`, and `permission_audit_reason` are used in `QueryRecordsHandler.execute` but ignored or partially dropped in `test_action_query` pre-detection.
4. **Architectural Recommendation (RECOMMENDATION):**
   - The Debug Query path must **not maintain a separate query engine or bypass QueryRecordsHandler.execute**.
   - It should pass configurations through `QueryRecordsHandler.execute` using a dedicated **Diagnostic Mode Context** (`{"test_mode": True, "diagnostic_limit": 1}`) that preserves normal permissions, gracefully reports unresolved dynamic context variables without failing SQL execution, and returns both structured schema metadata and diagnostic warnings.

---

## 1. What is "Refresh Schema (Debug Query)" Today?

### 1.1 UI Representation & Declarations
- **FACT:** In `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue` (lines 491–499), the button is declared as:
  ```html
  <div class="config-section section-card test-section">
      <button
          class="btn btn-xs btn-primary shadow-sm"
          @click="test_query"
          :disabled="readOnly"
          tabindex="0"
      >
          <i class="fa fa-flask mr-1"></i> {{ __("Refresh Schema (Debug Query)") }}
      </button>
      <span v-if="test_status" class="ml-2 text-muted font-weight-bold">{{ test_status }}</span>
  </div>
  ```
- **FACT:** When clicked, it sets `test_status.value = "Debugging..."` and calls `frappe.call` with method `flexirule.ruleflow.api.test_action_query`.
- **FACT:** In addition to manual clicks, `QueryRecordsConfig.vue` automatically invokes `debounced_schema_update` (lines 1478–1505) via a deep Vue `watch` on configuration changes (`order_by_rows`, `config`, `report_filter_values`, `mode`, `reference_doctype`).

---

## 2. Comprehensive Trace & Execution Path Analysis

Below is the exact, source-backed step-by-step trace comparing the **Debug Query Path** and the **Runtime Execution Path**.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                CLIENT-SIDE (Vue 3)                               │
├──────────────────────────────────────────────────────────────────────────────────┤
│ User clicks "Refresh Schema (Debug Query)"  OR  Local Config Changes              │
│   ├─ test_query()                           ├─ debounced_schema_update()        │
│   │    ├─ sets test_status = "Debugging..." │    ├─ debounce (500ms)           │
│   │    └─ frappe.call("test_action_query")   │    └─ frappe.call(silent=true)   │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ RPC Request (HTTP POST)
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             SERVER-SIDE (api.py)                                 │
├──────────────────────────────────────────────────────────────────────────────────┤
│ flexirule.ruleflow.api.test_action_query(rule_name, action_id, overrides)       │
│   ├─ 1. Load Rule doc & locate Action                                            │
│   ├─ 2. Apply UI overrides to Action in-memory                                   │
│   ├─ 3. Fetch sample document (rule.document_type, limit=1) -> context_doc        │
│   ├─ 4. Initialize RuleEngine(rule, {"test_mode": True})                         │
│   ├─ 5. Pre-detect schema (Static metadata inspection for Query List/Doc/Count)  │
│   ├─ 6. Execute Handler: HandlerRegistry.get("Query Records").execute()          │
│   ├─ 7. Refine schema from execution result (For Query Report & dictionary lists) │
│   └─ 8. Return {"success": True, "result": result, "schema": schema, "duration"} │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ Handler Dispatch
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   BACKEND HANDLER (query_records.py)                             │
├──────────────────────────────────────────────────────────────────────────────────┤
│ QueryRecordsHandler.execute(action, context, engine)                             │
│   ├─ 1. Check permissions (can_ignore_permissions)                              │
│   ├─ 2. Apply input_mapping if present                                           │
│   ├─ 3. Dispatch to mode handler:                                                │
│   │    ├── _query_list    -> frappe.get_list()                                   │
│   │    ├── _query_doc     -> frappe.get_doc() / get_cached_doc()                 │
│   │    ├── _exist_record  -> frappe.get_list(limit=1)                            │
│   │    ├── _query_report  -> frappe.desk.query_report.run()                      │
│   │    ├── _count_records -> frappe.db.count()                                   │
│   │    ├── _aggregate     -> frappe.db.sql() / QB                                │
│   │    └── _group_by      -> frappe.get_list(group_by=...)                      │
│   └─ 4. Return (result, next_action)                                             │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Boundary-by-Boundary Comparison Matrix

| Boundary | Function / Location | Input | Expected Output | Actual Debug Behavior | Actual Runtime Behavior | Divergence Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Client Call** | `test_query` (`QueryRecordsConfig.vue:1450`) | Node overrides & Rule Name | Response envelope with schema | Sends full `overrides` object containing node data | N/A (Client only) | **Identical Payload** |
| **Context Prep** | `test_action_query` (`api.py:993`) | `rule_name`, `context_doc` | Simulated execution context | Fetches 1 recent record (`frappe.get_all(limit=1)`). If none exists, `doc = None` | Uses active trigger `doc` and execution `vars` | **DIVERGENCE:** Debug context lacks `vars` and active transaction state |
| **Pre-Detection** | `test_action_query` (`api.py:1020-1111`) | `action.config` | Static schema prediction | Builds schema array directly from `frappe.get_meta` before running query | Skipped (Runtime returns raw query results) | **INTENTIONAL:** Pre-detection provides fallback schema if query fails |
| **Handler Exec** | `test_action_query` (`api.py:1115`) | `action`, `context`, `engine` | Executed query result | Calls `QueryRecordsHandler.execute()` directly | Calls `QueryRecordsHandler.execute()` via `RuleEngine` | **MATCH:** Debug mode reuses the identical backend handler |
| **Post Refine** | `test_action_query` (`api.py:1120-1160`) | `result` | Final schema | Inspects `result["columns"]` (for reports) or result keys | Assigns result directly to engine context variable | **MATCH:** Converts result structure into schema DTOs |

---

## 3. Complete Query Records Configuration Transmission Matrix

This matrix tracks every configuration field across the client-side Vue component (`QueryRecordsConfig.vue`), the debug API (`test_action_query`), the backend handler (`QueryRecordsHandler.execute`), and the native Frappe database API (`frappe.get_list`, `frappe.get_doc`, `query_report.run`).

| Configuration Field | Sent in Debug Payload? | Handled by `test_action_query` Pre-Detection? | Used by `QueryRecordsHandler.execute`? | Passed to Native Frappe API? | Evidence (File & Lines) | Status / Divergence |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **`reference_doctype`** | Yes | Yes | Yes | Yes | `api.py:1028`, `query_records.py:323` | **Full Parity** |
| **`operation` (mode)** | Yes | Yes | Yes | Yes | `api.py:1027`, `query_records.py:322` | **Full Parity** |
| **`fields`** | Yes | Yes | Yes | Yes | `api.py:1030`, `query_records.py:840` | **Full Parity** |
| **`filters`** | Yes | No (Ignored in pre-detect) | Yes | Yes | `api.py:1020`, `query_records.py:730` | **Runtime Filter Evaluation Divergence** (Dynamic expressions fail if context missing) |
| **`order_by`** | Yes | No | Yes | Yes | `query_records.py:853` | **Full Parity** (Qualified with `_qualify_order_by`) |
| **`limit_type`** | Yes | No | Yes | Yes | `query_records.py:841` | **Full Parity** |
| **`limit`** | Yes | No | Yes | Yes | `query_records.py:847` | **Full Parity** |
| **`group_by`** | Yes | No | Yes | Yes | `query_records.py:856` | **Full Parity** |
| **`distinct`** | Yes | No | Yes | Yes | `query_records.py:868` | **Full Parity** |
| **`parent_doctype`** | Yes | No | Yes | Yes | `query_records.py:870` | **Full Parity** |
| **`ignore_permissions`** | Yes | No | Yes | Yes | `query_records.py:325` | **Full Parity** (Requires System Manager role) |
| **`permission_audit_reason`**| Yes | No | Yes (via audit check) | No | `permissions.py:can_ignore_permissions` | **Full Parity** |
| **`fetch_strategy`** | Yes | Partial (Query Doc) | Yes | Yes | `api.py:1034`, `query_records.py:898` | **Full Parity** |
| **`doctype_name`** | Yes | No | Yes | Yes | `query_records.py:887` | **Full Parity** |
| **`docname`** | Yes | No | Yes | Yes | `query_records.py:922` | **Full Parity** |
| **`report_name`** | Yes | No (Refined post-exec)| Yes | Yes | `api.py:1126`, `query_records.py:981` | **Post-Execution Dependent** |

---

## 4. Deep-Dive Divergence Analysis by Query Records Mode

FlexiRule supports **10 Query Records operations/modes**. Below is the audit evaluation for each mode comparing Debug Query and Runtime execution.

### Mode Support Matrix

| Query Mode | Debug Query Supported? | Same Config Passed? | Same Backend Handler? | Filter Normalization Parity? | Permission Parity? | Schema Meaningful? | Primary Vulnerability / Point of Divergence |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Query List** | Yes | Yes | Yes | Yes | Yes | Yes | Missing context for dynamic filter expressions (`doc.*`). |
| **Query Doc** | Yes | Yes | Yes | Yes | Yes | Yes | Unresolved `docname` expression returns `None` doc without schema error. |
| **Exist Record** | Yes | Yes | Yes | Yes | Yes | Yes (Boolean) | Pre-detection returns empty; schema inferred as `[]` or `[name]`. |
| **Query Report** | Partial | Yes | Yes | Yes | Yes (Report permissions) | Yes (Columns) | **CRITICAL:** Column schema detection is 100% post-execution dependent. If missing report filter causes exception, schema returns `[]`. |
| **Count** | Yes | Yes | Yes | Yes | Yes | Yes (`result: Int`) | Pre-detection forces schema `[{"fieldname": "result", "fieldtype": "Int"}]`. |
| **Sum** | Yes | Yes | Yes | Yes | Yes | Yes (`result: Float`) | Requires `config.field`; pre-detection returns `[{"fieldname": "result"}]`. |
| **Average** | Yes | Yes | Yes | Yes | Yes | Yes (`result: Float`) | Same as Sum. |
| **Min** | Yes | Yes | Yes | Yes | Yes | Yes (`result: Data`) | Same as Sum. |
| **Max** | Yes | Yes | Yes | Yes | Yes | Yes (`result: Data`) | Same as Sum. |
| **Group By** | Yes | Yes | Yes | Yes | Yes | Yes (List of Dicts)| Pre-detection fails; relies entirely on post-execution result keys. |

---

## 5. Definition & Meaning of "Schema"

A core finding of this audit is clarifying what “Schema” actually means in FlexiRule:

### 5.1 DocType Metadata Schema vs Configured Query Records Runtime Result Schema
- **DocType Metadata Schema (FACT):**
  - Defines the static structural fields of a Frappe DocType (e.g. `User` has `email`, `first_name`, `enabled`).
  - Obtained via `frappe.get_meta("User")`.
- **Configured Query Records Runtime Result Schema (FACT):**
  - Defines the **exact payload shape** produced by executing the configured Query Records action.
  - Examples:
    - If Query List specifies `fields: ["name", "email"]`, the runtime result schema is `[{fieldname: "name"}, {fieldname: "email"}]`.
    - If Query List specifies dotted child table fields `items.item_code`, the runtime result schema is `[{fieldname: "items.item_code"}]`.
    - If Query Report runs, the runtime result schema is derived from report `columns` (`[{fieldname: "account", label: "Account"}]`).
    - If Count runs, the runtime result schema is `[{fieldname: "result", fieldtype: "Int"}]`.

### 5.2 What "Refresh Schema (Debug Query)" Refreshes
- **FACT:** In FlexiRule, `resolved_output_schema` stored on the `Rule Action` node is consumed by downstream nodes in the Visual Builder (e.g., `InputPanel.vue`, `ConditionStep.vue`, `OutputPanel.vue`) to populate variable selection dropdowns for subsequent steps.
- **RECOMMENDATION:** The button MUST refresh the **Configured Query Records Runtime Result Schema**, NOT raw DocType metadata. Downstream steps need to know the exact output fields that will exist in `vars.<return_variable>` when the rule runs.

---

## 6. Root Cause & First Point of Failure Analysis

### Why is the button currently failing or producing empty/stale schemas?

The audit identified **4 main failure mechanisms**:

#### Mechanism 1: Unresolved Dynamic Expressions in Filters (`FACT`)
- **Evidence:** In `api.py:test_action_query`, line 1005:
  ```python
  doc = frappe.get_doc(rule.document_type, recent[0])
  ```
- **Observed Failure:** If the Query Records filter uses a variable from a previous step (e.g. `vars.customer_id` or `doc.custom_field` on a newly created unsaved document), `test_action_query` executes with a random database record or `doc = None`.
- **First Point of Failure:** `QueryRecordsHandler._resolve_value_expression_with_context` throws an error or evaluates `vars.customer_id` to `""` (empty string). Frappe then executes SQL like `WHERE customer = ''`, returning 0 records. If pre-detection was not triggered, result-based schema extraction gets an empty array `[]`.

#### Mechanism 2: Query Report Filter Mandate Exception (`FACT`)
- **Evidence:** `query_records.py:981` (`_query_report`) calls `frappe.desk.query_report.run()`.
- **Observed Failure:** Many standard Frappe reports require specific mandatory filters (e.g. `company`, `fiscal_year`).
- **First Point of Failure:** In `api.py`, `Query Report` schema pre-detection is omitted (lines 1025–1098). Schema detection relies *entirely* on line 1126 post-execution. When `run_report` raises `frappe.MandatoryError` or `ValidationError`, `test_action_query` catches the exception in line 1162 and returns:
  ```json
  {"success": false, "error": "Mandatory filter missing", "schema": []}
  ```
  The UI catches this in `test_query` and sets `test_status = "Failed"`, wiping out `resolved_output_schema`.

#### Mechanism 3: Vue Local Sync vs RPC Race Condition (`FACT`)
- **Evidence:** `QueryRecordsConfig.vue` contains both `update_resolved_schema_local()` (instant client-side metadata lookup) and `debounced_schema_update()` (RPC to `test_action_query`).
- **Observed Failure:** When editing fields, `update_resolved_schema_local()` immediately populates `props.node.data.resolved_output_schema`. 500ms later, `debounced_schema_update()` returns from the server. If the server query fails due to Mechanism 1 or 2, `debounced_schema_update` silences the error but fails to update the schema, or `test_query()` overwrites the valid local schema with `[]`.

#### Mechanism 4: Child Table SQL Qualification Divergence (`FACT`)
- **Evidence:** `query_records.py:730` (`_resolve_query_filters`) compiles dotted filters like `["items.item_code", "=", "X"]` into 4-tuples `["Sales Invoice Item", "item_code", "=", "X"]`.
- **Observed Failure:** If `parent_doctype` is required for querying child tables directly and is missing in config, `frappe.get_list` raises a Database / SQL Join error during debug execution, causing debug query failure.

---

## 7. Dynamic Values & Resolver Behavior in Debug Mode

### 7.1 How Runtime Receives Context (`FACT`)
In `RuleEngine.execute(doc)`, context is constructed as:
```python
context = {
    "doc": doc,
    "old_doc": getattr(doc, "_doc_before_save", None),
    "vars": {},
    "frappe": SafeFrappeAPI(),
}
```
As actions execute, outputs are written to `context["vars"][action.return_variable]`.

### 7.2 How Debug Query Receives Context (`FACT`)
In `api.py:test_action_query`:
```python
engine = RuleEngine(rule, {"test_mode": True})
context = engine._initialize_context(doc)
```
- `vars` is completely empty (`{}`).
- `doc` is a random recent record from the database.

### 7.3 Evaluation of Dynamic Resolver Failures (`FACT`)
When a filter value is `{"mode": "variable", "value": "vars.selected_customer"}`:
- Runtime resolves it via `_resolve_value_expression_with_context`.
- Debug Query looks up `vars.selected_customer` in `{}` and gets `None` / `""`.
- The query executes as `WHERE customer = ''`.

### 7.4 Architectural Policy Recommendation (`RECOMMENDATION`)
> **“Debug Query must never silently substitute empty strings, stale values, arbitrary defaults, or otherwise alter dynamic values merely to make the query execute.”**

**Recommended Behavior:**
1. Debug Query should inspect the configuration for unresolved `vars.*` or `doc.*` references.
2. If `test_context` (from the UI simulation panel / `useUIStore.test_context`) is provided, use it.
3. If dynamic variables cannot be resolved, Debug Query should **fall back gracefully to static metadata projection** and include an explicit diagnostic warning in the response:
   ```json
   {
     "success": true,
     "schema": [...],
     "diagnostics": {
       "warnings": ["Filter 'customer' uses dynamic variable 'vars.customer_id' which is unavailable in debug mode. Schema generated from metadata projection."],
       "unresolved_variables": ["vars.customer_id"]
     }
   }
   ```

---

## 8. Child Tables, Relationships & Field Qualification Analysis

### 8.1 Child Table Field Paths (`FACT`)
- Users configure child table fields using dotted syntax: `roles.role`, `user_emails.email_account`.
- In `query_records.py`:
  - **Filter Normalization (`_resolve_filter_doctype_and_field`):** Resolves `roles.role` by inspecting `frappe.get_meta(reference_doctype)`. If `roles` is a Table field pointing to child DocType `Has Role`, it translates the filter to `["Has Role", "role", "=", "System Manager"]`.
  - **Order By Qualification (`_qualify_order_by`):** Qualifies field paths to prevent SQL ambiguity: `` `tabHas Role`.`role` ASC ``.
  - **Field Selection (`_query_list`):** Passes `["name", "roles.role"]` to `frappe.get_list`. Frappe automatically handles the parent-child JOIN query.

### 8.2 Parity Between Debug and Runtime (`FACT`)
- Because `test_action_query` invokes `QueryRecordsHandler.execute()` directly, **both Debug Query and Runtime Query Records use the exact same child table filter resolution, SQL qualification, and `frappe.get_list` join logic**.
- Invalid SQL expressions like `` `tabUser`.`roles`.`role` `` are **NOT** generated. The backend generates standard Frappe parent-child SQL joins.

---

## 9. Security & Permissions Analysis

### 9.1 Permission Enforcement (`FACT`)
- In `query_records.py:325`:
  ```python
  ignore_permissions = can_ignore_permissions(action, context, throw=True)
  ```
- `can_ignore_permissions` checks if `action.ignore_permissions` is enabled AND verifies that the executing user has the `System Manager` role (or `permission_audit_reason` is supplied).
- If a non-System Manager attempts to check `Skip Permissions` in the UI, `can_ignore_permissions` raises `frappe.PermissionError`.

### 9.2 Debug Query Security Parity (`FACT`)
- `test_action_query` is decorated with `@frappe.whitelist()`.
- It calls `_require_api_access()`, which delegates to `require_builder_access()` (checking FlexiRule Rule Builder read/write access).
- When executing the query handler, `test_action_query` passes `action.ignore_permissions` directly to `QueryRecordsHandler.execute()`.
- **Security Finding:** Debug Query **does not silently elevate privileges or bypass permissions**. Non-System Managers cannot use Debug Query to bypass permissions on arbitrary DocTypes.

---

## 10. Proposed Future Contract & Architectural Direction

### 10.1 Unified Architecture Principles
1. **Single Query Handler:** `test_action_query` must continue to invoke `QueryRecordsHandler.execute()`. No second query engine should be introduced.
2. **Robust Schema Pre-Detection & Fallback:** If query execution fails due to missing runtime context or missing report filters, `test_action_query` MUST return the pre-detected metadata schema along with diagnostic warnings rather than failing completely.
3. **Structured Response Envelope:** The API contract must return explicit schema metadata and diagnostic details.

### 10.2 Proposed Future API Contract

#### Input Payload (`frappe.call` args to `test_action_query`)
```json
{
  "rule_name": "sales_discount_rule",
  "action_id": "act_query_customers",
  "overrides": {
    "action_type": "Query Records",
    "operation": "Query List",
    "reference_doctype": "Customer",
    "config": {
      "fields": ["name", "customer_name", "customer_group"],
      "filters": [["Customer", "disabled", "=", 0]],
      "order_by": "customer_name asc",
      "limit": 10
    },
    "ignore_permissions": 0
  },
  "test_context": {
    "vars": {}
  }
}
```

#### Output Response Envelope
```json
{
  "success": true,
  "schema": [
    {
      "fieldname": "name",
      "label": "ID",
      "fieldtype": "Data",
      "options": null,
      "mandatory": 1
    },
    {
      "fieldname": "customer_name",
      "label": "Customer Name",
      "fieldtype": "Data",
      "options": null,
      "mandatory": 1
    },
    {
      "fieldname": "customer_group",
      "label": "Customer Group",
      "fieldtype": "Link",
      "options": "Customer Group",
      "mandatory": 0
    }
  ],
  "diagnostics": {
    "execution_status": "Success",
    "execution_duration_ms": 12.4,
    "rows_returned": 5,
    "unresolved_variables": [],
    "warnings": []
  }
}
```

---

## 11. Required Test Suite Plan for Future Implementation

To ensure long-term stability and prevent regressions, a future implementation task should add tests covering:

### 11.1 Frontend Cypress UI Tests
- **Button Interaction:** Verify clicking "Refresh Schema (Debug Query)" shows "Debugging..." loading state and updates `resolved_output_schema`.
- **Stale Schema Clearing:** Verify changing `reference_doctype` or `operation` updates/clears output schema.
- **Error Display:** Verify user-friendly error message when an invalid report or non-existent DocType is configured.

### 11.2 Backend Server-Side Tests (`test_query_records_debug.py`)
- **Query List Parity:** Test `test_action_query` returns correct field types for parent and child fields (`items.item_code`).
- **Query Doc Parity:** Test `test_action_query` for Single and standard DocTypes.
- **Query Report Parity:** Test `test_action_query` with standard report (`General Ledger`), verifying column schema extraction.
- **Dynamic Context Handling:** Test `test_action_query` with unresolved `doc.supplier` filter, verifying it returns metadata schema and diagnostic warning without crashing.
- **Permission Bypassing Security:** Verify non-System Manager user receives `PermissionError` when attempting `ignore_permissions: 1` in Debug Query.

---

## 12. Final Evidence Summary & Conclusion Matrix

| Deliverable Question | Audit Answer | Evidence Classification & Source |
| :--- | :--- | :--- |
| **1. What is "Refresh Schema"?** | A button and background watch trigger in `QueryRecordsConfig.vue` that requests runtime return schema for downstream nodes. | **FACT:** `QueryRecordsConfig.vue:492`, `1450`, `1480` |
| **2. What does `test_query` do?** | Invokes `test_action_query` RPC with UI node overrides and updates `resolved_output_schema`. | **FACT:** `QueryRecordsConfig.vue:1450` |
| **3. What does `debounced_schema_update` do?** | Debounced (500ms) background watch calling `test_action_query` silently on local config changes. | **FACT:** `QueryRecordsConfig.vue:1480` |
| **4. What does `test_action_query` do?** | Loads action, applies overrides, pre-detects static metadata, executes `QueryRecordsHandler`, refines schema. | **FACT:** `api.py:949–1198` |
| **5. How does it differ from runtime?** | Debug lacks full active execution `context` (`vars`) and operates in isolated test mode. | **FACT:** `api.py:993`, `query_records.py:320` |
| **6. Which modes are supported?** | All 10 Query Records modes (`Query List`, `Query Doc`, `Exist Record`, `Query Report`, `Count`, Aggregations, `Group By`). | **FACT:** `api.py:1025–1150` |
| **7. Which fields are lost/transformed?** | Filters with dynamic variables lose context; report filters without values trigger report exceptions. | **FACT:** `api.py:1005`, `query_records.py:981` |
| **8. What is meant by "schema"?** | Configured Query Records Runtime Result Schema (list of field DTOs for downstream variables). | **INFERENCE / RECOMMENDATION** |
| **9. Why is it currently failing?** | Context starvation for dynamic filters & unhandled exceptions during report execution wiping schema. | **FACT:** `api.py:1162`, `query_records.py:981` |
| **10. First point of failure?** | `_resolve_value_expression_with_context` or `query_report.run` throwing exception before schema return. | **FACT:** `api.py:1162` |
| **11. Failure classification?** | Combination of backend context starvation and pre-detection/post-refinement coupling. | **FACT** |
| **12. How are dynamic values handled?** | Unresolved `vars.*` resolve to `None`/`""`, causing query execution failure or empty results. | **FACT:** `query_records.py:730` |
| **13. How are child tables handled?** | Both debug and runtime normalize child filters to 4-tuples and qualify `order_by` correctly. | **FACT:** `query_records.py:780`, `820` |
| **14. How are permissions handled?** | Enforced via `can_ignore_permissions` requiring System Manager role in both modes. | **FACT:** `query_records.py:325` |
| **15. Proposed contract?** | Bounded diagnostic execution returning combined metadata schema + diagnostic warnings payload. | **RECOMMENDATION** |
| **16. Required test coverage?** | Cypress UI button tests and server-side mode, report, permission, and dynamic context tests. | **RECOMMENDATION** |

---
*End of Deep Audit Report.*
