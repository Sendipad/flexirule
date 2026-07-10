# Architectural Engineering Review: Query Records Refactor & Frappe Native Capability Alignment

This report presents a thorough secondary engineering review of the proposed Query Records refactor. Its goal is to align FlexiRule's querying mechanism with the native capability of the Frappe Framework (v15+), eliminating redundant layers of backend metadata lookup, custom SQL parsing, and manual permission wrappers.

The fundamental design principle of this alignment is: **"FlexiRule should orchestrate Frappe, not replace or duplicate Frappe."**

---

## 1. Current Plan Problems (Duplicated Functionality)

By analyzing the previous refactor proposal against native Frappe v15 source code, we have identified several areas of duplication where FlexiRule was attempting to rebuild database query parsing, join resolution, or permission structures that Frappe already implements natively.

| Area | Refactor Current Proposal | Frappe Native Capability | Recommendation (The Alignments) |
| :--- | :--- | :--- | :--- |
| **Child Filters / Dotted Key Parsing** | Rebuild a custom recursive parser on the backend (`_normalize_dotted_filter`) to split dots (`fields.fieldname`), fetch parent metadata, look up child doctype options, and compile standard 4-value SQL list filters. | Frappe’s `DatabaseQuery` natively supports 4-value list-of-lists filter formats `["Child DocType", "child_fieldname", "operator", "value"]` when queried directly, or parent-nested notation `["Parent DocType", "child_table.fieldname", "=", "value"]` which automatically triggers left-joins. | **Move transformation responsibility completely to the UI layer (Frontend).** The Vue configuration component (`QueryRecordsConfig.vue`) already holds/loads parent metadata. If a child field with a dot is selected, the frontend should directly serialize and store the standard 4-value native Frappe dictionary/array structure. The backend should only validate schema rules and pass the final parameters through. |
| **Permissions Enforcements** | Introduce manual permission-gating wrappers via `frappe.has_permission(...)` before running query executions. | Frappe’s `get_list()` natively acts as the single permission authority. It handles fine-grained role permissions, owner conditions, user-sharing filters, and field-level permissions. | **Remove all manual backend permission wrappers.** Do not perform manual `has_permission` checks before querying. Let `get_list()` remain the single source of truth for permission evaluation and fail with standard Frappe exception paths. |
| **Parent Discovery for Child Tables** | Build a backend "Parent DocType Resolver" that queries database metadata schemas at runtime to find which parent doctype is linked to a target child table. | Frappe’s `get_list()` accepts a `parent_doctype` keyword argument and natively resolves permissions against the parent-child relational tree. | **Move Parent Discovery to the Frontend.** If target doctype is identified as a child table (`istable` is True), the frontend configuration displays a mandatory dropdown of parent doctypes (which can be pre-filled automatically or selected by the user). This value is stored as part of the config (`{"parent_doctype": "Parent DocType"}`) and passed directly as a backend argument. Avoid doing runtime DB metadata lookups inside execution paths. |
| **DISTINCT / Deduplication** | Build custom backend deduplication logic or SQL aggregation wrappers to prevent duplicate parent rows when querying with child fields. | Frappe's `get_list()` natively supports the `distinct=True` kwarg, prepending `DISTINCT` in the compiled select projection. | **Expose DISTINCT purely as a UI toggle.** Pass the boolean toggle value directly from the frontend config to the backend `get_list(..., distinct=True)` kwarg. No custom backend logic. |
| **Query Records Architecture** | Construct a custom abstract query builder class/context (`QueryContext`) to represent filters, fields, distinct, and parent doctype before execution. | Frappe’s native keyword mapping (`**kwargs`) already acts as a robust context carrier directly into the `DatabaseQuery` class. | **Do not build a custom Query Builder abstraction.** Maintain the flat execution path and directly forward the mapped parameters dictionary to `frappe.get_list`. |

---

## 2. Revised Architecture

The revised architecture establishes a clean separation of concerns. The frontend manages structural metadata selection and dynamic data bindings, while the backend focuses strictly on validation, resolving runtime variable values, and forwarding payloads directly to native Frappe APIs.

```
       [ Rule Builder Frontend (Vue 3) ]
       ├── Metadata selection & Parent/Child relation audit
       ├── Dynamic value bindings (e.g. {{trigger.customer}})
       ├── Structure filters to native Frappe formats (4-value list-of-lists)
       └── Store config: fields, filters, parent_doctype, distinct
                       │
                       ▼ (JSON Action Config Payload)
       [ FlexiRule Execution Backend (Python) ]
       ├── Validate configuration schema
       ├── Resolve dynamic variables using context (Runtime Resolver)
       ├── Bypass custom SQL generation & permission wrappers
       └── Call native Frappe APIs:
             ├── get_list(DocType, filters, fields, parent_doctype, distinct, limit_page_length)
             └── get_doc / get_cached_doc (for Query Doc)
```

### Frontend Responsibility
1. **Metadata Selection**: Identify whether the target doctype is a parent table or a child table.
2. **Child Field Selection & Formatting**: Detect if a field contains dotted paths (`fields.fieldname`). Resolve child table metadata directly on the frontend and generate the 4-value native Frappe filter format:
   ```json
   {
     "doctype": "DocField",
     "fieldname": "fieldname",
     "operator": "=",
     "value": "value"
   }
   ```
3. **Dynamic Value Binding**: Allow users to bind fields to variables, expressions, or runtime context values (e.g., `{{trigger.customer}}`) using semantic descriptors.
4. **Query Configuration**: Provide toggles for `distinct` and select fields for `parent_doctype` strictly when required based on metadata checks.

### Backend Responsibility
1. **Configuration Validation**: Verify that the selected doctype and fields are valid.
2. **Runtime Value Resolution**: Execute the runtime resolver to replace dynamic values (e.g., `{{trigger.customer}}`) with actual context values before querying.
3. **API Forwarding**: Call the native Frappe APIs (`get_list`, `get_cached_doc`) using the resolved filters and configuration arguments.
4. **Result Mapping**: Return results directly to the execution context.

---

## 3. Minimal Backend Changes

This section separates unavoidable backend changes from proposed custom logic that should be removed or questioned.

### KEEP (Unavoidable Backend Changes)
* **Aggregate Operations Security Fix (`get_all` -> `get_list`)**:
  Replace `frappe.get_all` with `frappe.get_list(..., limit_page_length=0)` inside `_count_records()`, `_aggregate()`, and `_group_by()`. This is essential because `frappe.get_all` overrides permissions bypass internally. Using `get_list` with `limit_page_length=0` ensures that the standard user's role-level and sharing permissions are fully checked during aggregate evaluations.
* **Pass `distinct` parameter**:
  Extract the `distinct` boolean from `config` in `_query_list` and pass it directly to `frappe.get_list(..., distinct=distinct)`.
* **Pass `parent_doctype` parameter**:
  Extract `parent_doctype` from `config` when querying a Child DocType and pass it directly to `frappe.get_list(..., parent_doctype=parent_doctype)`.

### QUESTION (Re-evaluated & Simplified)
* **Dotted filter key normalization**:
  * *Audit Outcome*: Rather than building a recursive backend metadata parser that replicates `DatabaseQuery` logic and risks runtime exceptions, the frontend should perform the splitting and metadata mapping at configuration time.
  * *Backend fallback*: If a dotted filter still reaches the backend, the backend should only run a simple, lightweight helper that splits the first dot and formats it as a list filter (e.g. `[child_doctype, child_field, operator, value]`) without triggering nested database lookups or custom SQL compilation.

### REMOVE (Eliminated Duplications)
* **Duplicated Metadata Lookup**: Remove custom parent resolver logic or child metadata queries from the backend execution path.
* **Custom SQL Handling**: Avoid any custom SQL string interpolation, `LEFT JOIN` generation, or manual string joins. Let Frappe handle joins automatically based on the list of fields and 4-value filters.
* **Permission Wrappers**: Eliminate manual `frappe.has_permission(...)` checks before calling `get_list`. Trust Frappe's native exceptions and handling inside `get_list`.

---

## 4. Migration Sequence Update

To ensure maximum safety and avoid regressions, the migration is structured into sequential phases:

### Phase 1: Security Fixes (Immediate Parity)
* **Backend**: Replace `get_all` with `get_list` in aggregate modes (`_count_records`, `_aggregate`, `_group_by`, `_exist_record`) with `limit_page_length=0`.
* **Backend**: Ensure any manual backend permission-checking wrappers are removed in favor of native `get_list` execution flow.

### Phase 2: Frontend Query Configuration Improvements
* **Frontend**: Add a "Deduplicate Rows (DISTINCT)" checkbox toggle under the Query List settings.
* **Frontend**: Conditionally display the "Parent DocType" selection box when target doctype `istable` is True.
* **Backend**: Extract `distinct` and `parent_doctype` keys from `config` and map them directly into `frappe.get_list()` keyword arguments.

### Phase 3: Runtime Resolver Improvements (Separation of Concerns)
* **Frontend**: Support serializing child-table filters into native 4-value formats during configuration.
* **Backend**: Ensure the filter resolver strictly substitutes context variable values (e.g. `{{trigger.customer}}`) into final query filters, keeping variable substitution completely separate from SQL query generation.

### Phase 4: Optional Enhancements
* Move shared filters normalization utilities into a generic helper directory (e.g., `flexirule/ruleflow/utils/filters.py`) to be used consistently across all action handlers.
