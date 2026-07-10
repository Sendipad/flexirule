# Query Records Refactor Architecture Review & Frappe Native Capability Alignment

## 1. Executive Summary

This architecture review presents a second engineering pass of the **Query Records** action handler migration plan. The goal is to maximize the utilization of native, built-in features provided by the **Frappe Framework (v15+)** and minimize the amount of custom code, custom parsers, and custom metadata lookups implemented within FlexiRule.

By aligning our design directly with Frappe's native capabilities, we eliminate redundant backend logic, prevent performance bottlenecks from duplicate database lookups in execution hot-paths, and guarantee long-term compatibility with future Frappe releases.

### Key Redesign Objectives:
1.  **Eliminate Backend Filter Normalization**: Move the responsibility of compiling dotted-path child table filters from the backend to the frontend configuration layer.
2.  **Rely Natively on Parent-DocType Permission Check**: Let Frappe handle parent-child validation and permission checks natively through standard `frappe.get_list(child_doctype, parent_doctype=parent)`.
3.  **Use Native DISTINCT Support**: Do not implement any custom distinct projection sorting or deduplication. Pass `distinct=config.get("distinct")` directly to `get_list`.
4.  **Enforce Permissions via get_list for Aggregates**: Do not add manual permission pre-checks. Simply switch `get_all` to `get_list(limit_page_length=0)` to let Frappe serve as the sole permission authority.

---

## 2. Current Plan Problems (Duplication Analysis)

The table below audits the previous refactoring proposal, highlighting areas of unnecessary duplication of Frappe capabilities and providing aligning recommendations:

| Refactoring Area | Previous Proposal | Frappe Native Capability | Alignment Recommendation |
| :--- | :--- | :--- | :--- |
| **Child table filter parsing** | Resolve child doctype and table field metadata inside a custom backend dotted-path parser. | `DatabaseQuery` natively supports child filters if formatted in the explicit list of list format: `[["Child DoType", "field", "op", "value"]]`. | **Move to Frontend Configuration**: Configure `QueryRecordsConfig.vue` to save the selected filter metadata directly in the native 4-value list-of-lists structure. Completely remove custom backend parsing. |
| **Child table permissions** | Implement a custom Parent DocType resolver and execute manual `DocField` schema lookups in the backend execution path. | `frappe.get_list` natively supports and validates the parent-child relationship when passed `parent_doctype="Parent DocType"`. | **Expose in UI, Forward in Backend**: Let the UI detect table fields, offer available parent DocTypes, and store `parent_doctype`. The backend simply forwards the value to `frappe.get_list`. |
| **Security Validation in Aggregates** | Run manual `frappe.has_permission()` checks on the backend before executing aggregates under `get_all`. | `frappe.get_list` natively enforces role-permissions, document ownership restrictions, sharing conditions, and field-level permissions. | **Remove Manual Check**: Switch `get_all` to `get_list` and set `limit_page_length=0`. Do not write custom permission checks; let Frappe remain the single authority. |
| **Deduplication / DISTINCT** | Write custom distinct query compilation and PostgreSQL order-by clearing rules on the backend. | `frappe.get_list` natively accepts `distinct=True` and handles PostgreSQL's unique sorting/order-by constraints. | **Forward Native Parameter**: Forward `distinct=bool(config.get("distinct", False))` directly as a keyword argument to `get_list()`. |

---

## 3. Revised Architecture

The aligned architecture clearly segregates responsibilities across the configuration layer, runtime resolution layer, and query execution layer.

```
       [Rule Config Phase / Saved Schema]
                       │
                       ▼
       ┌───────────────────────────────┐
       │   Frontend Configuration      │
       ├───────────────────────────────┤
       │ - Metadata Discovery (Schema) │
       │ - Save child filters as list  │
       │ - Expose distinct & parent_dt │
       └───────────────┬───────────────┘
                       │
                       ▼ [Action Config JSON]
       ┌───────────────────────────────┐
       │     Runtime Resolver          │
       ├───────────────────────────────┤
       │ - Resolve Context variables   │
       │ - Map formula, Jinja, values  │
       │ - Output final static payload │
       └───────────────┬───────────────┘
                       │
                       ▼ [Statically-Resolved Filters & Fields]
       ┌───────────────────────────────┐
       │    Backend Handler (Refactored)│
       ├───────────────────────────────┤
       │ - Schema validation           │
       │ - Orchestrate frappe API calls│
       │ - Execute get_list() / get_doc│
       └───────────────┬───────────────┘
                       │
                       ▼ [API Kwargs]
       ┌───────────────────────────────┐
       │      Frappe Framework         │
       ├───────────────────────────────┤
       │ - Build Match/Share SQL       │
       │ - Compile physical left-joins │
       │ - Execute MariaDB/Postgres    │
       └───────────────────────────────┘
```

### 3.1 Frontend Responsibility (QueryRecordsConfig.vue)
- **Metadata Discovery**: Uses existing metadata functions to inspect target doctypes. Detects if target DocType is a child table (`istable` is true).
- **Direct Child Table Selection**: If `istable` is true, queries the database schema for parents and stores `parent_doctype` in config.
- **Dotted Path Normalization**: Intercepts dotted keys like `fields.fieldname` in selection and converts filters directly to `[["DocField", "fieldname", "=", "value"]]`.
- **Deduplication Option**: Exposes a "Deduplicate Rows (DISTINCT)" checkbox (only on list operations without aggregates) and stores it as a boolean.

### 3.2 Runtime Resolver Responsibility (ValueResolver)
- Executes compiled resolver graphs (`StaticResolver`, `VariableResolver`, etc.) against context variables (e.g. `{{doc.customer}}`).
- Outputs standard static string/number payloads.
- **De-coupling Guarantee**: The resolver only parses dynamic values. It has zero knowledge of database schemas, metadata joins, or SQL syntax, preventing code pollution in the evaluation path.

### 3.3 Backend Handler Responsibility (QueryRecordsHandler)
- **Validation**: Performs high-level backend validation ensuring the reference doctype exists.
- **Context Evaluation**: Invokes `apply_input_mapping` and resolves filter values using `_resolve_query_filters`.
- **API Call Orchestration**: maps parameters directly to standard keyword arguments and delegates queries to native Frappe APIs (`frappe.get_list`, `frappe.get_doc`, etc.).

---

## 4. Minimal Backend Changes

By shifting query configuration compilation to the frontend and relying on native Frappe APIs, we can remove the majority of the proposed backend changes:

### KEEP (Unavoidable refactors)
*   **Security Alignment**: Change `frappe.get_all` to `frappe.get_list` inside `_count_records()`, `_aggregate()`, and `_group_by()`, passing `limit_page_length=0` and `ignore_permissions=ignore_permissions`.
*   **DISTINCT Forwarding**: Read `distinct=bool(config.get("distinct"))` and pass it to `get_list` in `_query_list()`.
*   **Parent DocType Forwarding**: Read `parent_doctype=config.get("parent_doctype")` and pass it to `get_list` in `_query_list()`.

### QUESTION (Re-located to Frontend)
*   **Dotted Filter Normalization**: The backend dotted-path normalization algorithm is completely removed. Responsibility is shifted to `QueryRecordsConfig.vue` to directly compile filters into native child list-of-lists arrays upon saving.

### REMOVE (Redundant / Duplicated logic)
*   **Custom Parent DocType Resolver**: Deleted. No manual database searches or custom schemas lookups are run in the backend execution path.
*   **Manual `frappe.has_permission()` wrappers**: Deleted. We do not check permissions before calling `get_list`. We let `get_list` handle user sharing, doc ownership, and role match-conditions natively.
*   **Postgres Distinct Sort Cleansers**: Deleted. We let Frappe's `DatabaseQuery` automatically resolve distinct-sorting constraints.

---

## 5. Migration Sequence Update

To execute the refactoring path safely and incrementally, the following sequence is recommended:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              MIGRATION SEQUENCE                              │
├───────┬───────────────────────────────────┬───────────────┬──────────────────┤
│ Phase │ Refactor Focus                    │ Priority      │ Impact / Target  │
├───────┼───────────────────────────────────┼───────────────┼──────────────────┤
│   1   │ Fix Aggregate Permission Bypass   │ Critical      │ Backend Security │
│       │ (Switch get_all to get_list)      │               │                  │
├───────┼───────────────────────────────────┼───────────────┼──────────────────┤
│   2   │ Expose DISTINCT and Parent-DT in │ Medium        │ Frontend UI &    │
│       │ UI and forward in Backend handler │               │ Config Schema    │
├───────┼───────────────────────────────────┼───────────────┼──────────────────┤
│   3   │ Implement Frontend Filter         │ High          │ Frontend Config  │
│       │ Normalization for Child Table     │               │ Stability        │
│       │ Dotted Fields                     │               │                  │
└───────┴───────────────────────────────────┴───────────────┴──────────────────┘
```

### Risk Assessment of Revised Sequence:
- **Phase 1 (Critical)**: Changes only 4 lines in `query_records.py`. Extremely low regression risk; immediately secures the rule execution engine.
- **Phase 2 (Medium)**: Adds two configuration properties (`distinct` and `parent_doctype`) which default to safe fallback values (`False` and `None`), preserving 100% backward compatibility for existing rules.
- **Phase 3 (High)**: Shifts child table dotted-path translation to the frontend. Prevents any unhandled application crashes by ensuring only valid, natively-supported SQL list-filters are submitted to the backend.
