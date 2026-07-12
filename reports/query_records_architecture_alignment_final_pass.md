# Follow-up Architecture Review: Query Records Refactor — Frappe Native Alignment Final Pass

## 1. Executive Summary

This architecture review presents the final pass of the **Query Records** refactor alignment strategy. It refines the previous migration proposal by applying a strict, minimalist design principle:

> **«FlexiRule should generate valid Frappe-native query inputs. It should not implement its own query compiler, child table resolver, SQL normalization layer, or permission engine.»**

By adhering to this principle, we shift the responsibility of generating valid child-table list filters entirely to the frontend configuration layer (`QueryRecordsConfig.vue`). Consequently, we can completely eliminate all custom backend parsers, recursive dotted key normalizations, manual metadata lookups, and duplicate schema validation inside Python. This simplifies the backend `QueryRecordsHandler` to a pure, boilerplate-free orchestration layer that resolves dynamic variables at runtime and delegates SQL compilation, permissions, and database joins natively to the Frappe Query engine.

---

## 2. Remove Duplicate Frappe Query Logic

Every proposed backend helper and validation method in `query_records.py` is audited and classified below. By removing redundant backend logic, we avoid duplicating core capabilities already handled by Frappe.

### 2.1 Backend Helper Audit Table

| Backend Helper Method | Current Responsibility | Classification | Frappe Native Equivalent | Migration / Removal Plan |
| :--- | :--- | :---: | :--- | :--- |
| **`_doctype_has_field`** | Validates field existence on a DocType or child DocType. | **REMOVE** | `frappe.get_meta(doctype).has_field(fieldname)` | Delete this method. Standard metadata checks should be executed in the frontend UI or handled at runtime by Frappe. |
| **`_validate_filter_fields`** | Validates filter syntax and fields in Python before calling the API. | **REMOVE** | `DatabaseQuery` validation and sanitization checks. | Delete this method. Let `frappe.get_list` execute and let Frappe's native database/field exceptions propagate naturally. |
| **`_validate_doctype_field_references`** | Checks order-by, group-by, projection fields, and filters. | **REMOVE** | Standard metadata checking in core `DatabaseQuery`. | Delete this method. Rely on frontend-level schema validation and native backend execution gates. |
| **`_normalize_filters_for_backend`** | Manually parses and transforms dotted keys like `fields.fieldname` to child-table lists. | **REMOVE** | Native child table list formats compiled in the frontend. | Delete this method. Shift the responsibility of formatting child-table list filters to the frontend UI (`QueryRecordsConfig.vue`). |
| **`_resolve_timespan_range`** & **`_normalize_single_filter_operator`** | Custom date math and keyword-to-range operator mappings. | **REMOVE** | Native timespan operators inside `DatabaseQuery` (e.g. `["modified", "timespan", "this month"]`). | Delete these helper methods. Let the frontend compile UI operators (like `starts with` -> `["like", "value%"]`) and pass timespans directly to Frappe. |
| **`_coerce_between_value`** | coerces values for between operator filters. | **REMOVE** | Native array/string handling in `DatabaseQuery`. | Delete this method. |
| **`_extract_filter_value_payload`** | Extracts values from Pinia UI configuration payload objects. | **KEEP** | Standard payload resolution. | Retain this minimalist helper to map raw UI input structures before resolution. |

---

## 3. Child Table Query Handling

The refactored child-table query strategy is entirely driven by the frontend configuration phase, eliminating all custom child table join resolution in Python:

### Preferred Architecture Flow:
1.  **Frontend Config Layer**:
    - The rule builder configures a filter on a child field (e.g. `fields.fieldname`).
    - The UI detects that the parent `DocType` contains a Table field pointing to the child DocType `DocField`.
    - Upon saving the rule, the UI generates and stores the filter in the native Frappe child-list format:
      ```json
      {
        "reference_doctype": "DocType",
        "filters": [
          ["DocField", "fieldname", "=", "value"]
        ]
      }
      ```
2.  **Runtime Execution Layer**:
    - The runtime resolver processes the filters and replaces dynamic context tokens (e.g., `{{doc.fieldname}}`) with their final static value.
    - The backend handler receives the native, statically-resolved array of list-filters:
      ```python
      [["DocField", "fieldname", "=", "fieldname"]]
      ```
    - The backend simply forwards this array directly as keyword arguments:
      ```python
      frappe.get_list("DocType", filters=config.get("filters"))
      ```
    - **No dotted path splitting, metadata DocField lookups, physical table join construction, or SQL generation occurs in Python at execution time.**

---

## 4. Value Resolver Boundary Review

The runtime resolver (`ValueResolver`) remains strictly isolated, separating dynamic variable evaluation from query syntax compilation:

```
               [Value Resolver Boundary]

   ┌────────────────────────────────────────────────┐
   │ Allowed (In-Scope)                             │
   ├────────────────────────────────────────────────┤
   │ - Resolving variables (e.g. doc.fieldname)      │
   │ - Rendering Jinja template strings             │
   │ - Evaluating safe Python expressions           │
   │ - Returning static strings, numbers, booleans  │
   └───────────────────────┬────────────────────────┘
                           │ (Outputs flat, static inputs)
                           ▼
   ┌────────────────────────────────────────────────┐
   │ NOT Allowed (Out-of-Scope)                     │
   ├────────────────────────────────────────────────┤
   │ - Knowing about database schemas or DocTypes   │
   │ - Resolving parent-child or Link relationships │
   │ - Compiling SQL strings or LIKE wildcards      │
   │ - Generating where/join constraints            │
   └────────────────────────────────────────────────┘
```

---

## 5. QueryRecords Handler Simplification

By removing all custom validation helpers and parsing, the execution method in `query_records.py` is stripped down to a minimalist orchestration pattern:

```python
class QueryRecordsHandler(ActionHandler):
    action_type = "Query Records"

    def execute(self, action, context, engine):
        mode = action.operation
        reference_doctype = action.reference_doctype
        config = self._parse_config(action.config)
        ignore_permissions = can_ignore_permissions(action, context, throw=True)

        if not mode:
            frappe.throw(_("Operation/Mode is required for Query Records action"))
        if not reference_doctype:
            frappe.throw(_("Reference DocType is required for Query Records action"))

        # Resolve dynamic variables via apply_input_mapping
        action_config = frappe.parse_json(getattr(action, "config", "{}") or "{}")
        if action_config.get("input_mapping"):
            config = apply_input_mapping(context, action_config.get("input_mapping"), config)

        filters = self._resolve_filters_with_context(config.get("filters"), context, "filters", action)
        or_filters = self._resolve_filters_with_context(config.get("or_filters"), context, "or_filters", action)

        kwargs = {
            "doctype": reference_doctype,
            "filters": filters,
            "ignore_permissions": ignore_permissions,
            "limit_page_length": 0 if mode in ("Count", "Sum", "Average", "Min", "Max", "Group By") else (config.get("limit") or 20)
        }

        if or_filters:
            kwargs["or_filters"] = or_filters

        if config.get("distinct"):
            kwargs["distinct"] = True

        if config.get("parent_doctype"):
            kwargs["parent_doctype"] = config["parent_doctype"]

        # Delegate query execution directly to native Frappe APIs
        if mode == "Query List":
            kwargs["fields"] = config.get("fields", ["name"])
            kwargs["order_by"] = config.get("order_by", "modified desc")
            if config.get("group_by"):
                kwargs["group_by"] = config["group_by"]
            result = frappe.get_list(**kwargs)

        elif mode == "Query Doc":
            # Handles cached / direct document query
            result = self._query_doc_implementation(reference_doctype, config, context, action, ignore_permissions)

        elif mode == "Query Report":
            result = self._query_report_implementation(reference_doctype, config, context, action, ignore_permissions)

        elif mode == "Count":
            kwargs["fields"] = ["count(name) as _count"]
            rows = frappe.get_list(**kwargs)
            result = (rows and rows[0].get("_count")) or 0

        elif mode in ("Sum", "Average", "Min", "Max"):
            field = config.get("field", "name")
            agg_fn = {"Sum": "sum", "Average": "avg", "Min": "min", "Max": "max"}.get(mode)
            kwargs["fields"] = [f"{agg_fn}({field}) as result"]
            rows = frappe.get_list(**kwargs)
            result = (rows and rows[0].get("result")) or 0

        elif mode == "Group By":
            agg_field = config.get("agg_field", "name")
            group_field = config.get("group_by_field", agg_field)
            agg_fn = (config.get("agg_function") or "count").lower()
            safe_fn = agg_fn if agg_fn in {"sum", "avg", "min", "max", "count"} else "count"
            kwargs["fields"] = [group_field, f"{safe_fn}({agg_field}) as value"]
            kwargs["group_by"] = group_field
            result = frappe.get_list(**kwargs)

        next_action = action.next_step_if_true
        return result, next_action
```

---

## 6. Security Review

By replacing `get_all()` with `get_list()` for all aggregate operations, we align permissions behavior perfectly with Frappe's security engine:
- **Count / Metrics Permissions**: Standard user role constraints, document sharing limitations, and owner checks are automatically appended to the `WHERE` clauses compiled in SQL.
- **`ignore_permissions` Handling**: If standard users run queries under a rule where `ignore_permissions` is disabled, permissions are enforced. If `ignore_permissions` is configured, it is validated by `can_ignore_permissions` and audited, setting `ignore_permissions=True` to allow access under controlled conditions.
- **Security of Reports**: Report permissions can never be bypassed, while `ignore_permissions` only applies where explicitly intended (such as Query List/Database operations).
- **No Extra Code Overhead**: Bypasses the need for custom manual permissions evaluation wrappers.

---

## 7. Frontend Responsibility Review (QueryRecordsConfig.vue)

The frontend UI holds sole ownership of input compiling, ensuring only valid configurations are persisted to the database.

*   **Filter Generation**: Translates dotted fields (e.g. `fields.fieldname`) into standard, multi-value list filters specifying child doctypes natively.
*   **Deduplication (DISTINCT) Visibility**: Toggle DISTINCT option only under "Query List" mode, and disable/hide it if "Group By" or Aggregate functions are active.
*   **Parent DocType Selection**: Detects if target DocType is a child table (`istable` is true) and forces selection of a valid parent record type from schema mappings.

---

## 8. Final Target Architecture

The following diagram outlines ownership boundaries under the aligned design:

```
┌───────────────────────────────┐
│     QueryRecordsConfig.vue    │ ◄── [UI Ownership]
├───────────────────────────────┤     - Compile child dotted filters to list array
│  Generate Native JSON Filters │     - Expose parent_doctype & distinct toggles
└───────────────┬───────────────┘
                │
                ▼ [Saved Action Config JSON]
┌───────────────────────────────┐
│       Runtime Resolver        │ ◄── [Evaluation Ownership]
├───────────────────────────────┤     - Resolves Jinja and dynamic context fields
│   Output Resolved Query JSON  │     - Decoupled; returns static primitive values
└───────────────┬───────────────┘
                │
                ▼ [Static Parameters]
┌───────────────────────────────┐
│     QueryRecordsHandler       │ ◄── [Orchestration Ownership]
├───────────────────────────────┤     - Boilerplate-free; validates input shape
│   Call frappe.get_list()      │     - Simply forwards kwargs natively
└───────────────┬───────────────┘
                │
                ▼ [frappe.get_list(**kwargs)]
┌───────────────────────────────┐
│      Frappe Framework         │ ◄── [Compiler & Security Ownership]
├───────────────────────────────┤     - Applies role, share, and owner SQL conditions
│     Frappe DatabaseQuery      │     - Compiles left-joins and executes SQL
└───────────────────────────────┘
```

---

## 9. Updated Commit Plan

### Commit 1: Switch aggregates to get_list
*   **Files Modified**: `flexirule/ruleflow/core/action_handlers/query_records.py`
*   **Purpose**: Closes the security aggregate bypass. Replaces `get_all` with `get_list` inside `_count_records()`, `_aggregate()`, and `_group_by()`.
*   **Tests required**: Execute aggregate queries on restricted tables as a standard user. Assert `PermissionError` is thrown.
*   **Rollback Strategy**: Revert aggregates block to `get_all()`.

### Commit 2: Expose parent_doctype and distinct
*   **Files Modified**:
    - `flexirule/ruleflow/core/action_handlers/query_records.py`
    - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue`
*   **Purpose**: Passes `parent_doctype` and `distinct` parameters natively. Exposes the checkbox and dropdown options in the frontend.
*   **Tests required**: Query child DocTypes directly specifying a valid parent; verify query success. Query parent table and enable `distinct`; verify parent row deduplication.
*   **Rollback Strategy**: Set `distinct` to `False` and `parent_doctype` to `None`.

### Commit 3: Remove custom backend helpers & enable frontend filter compilation
*   **Files Modified**:
    - `flexirule/ruleflow/core/action_handlers/query_records.py`
    - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue`
*   **Purpose**: Delete `_doctype_has_field`, `_validate_filter_fields`, `_normalize_filters_for_backend`, and timespan date calculators from Python. Enable direct 4-value list-filter compilation inside the frontend save hook.
*   **Tests required**: Create a filter on a child field. Verify that saving compiles it to a list format and executes without database error.
*   **Rollback Strategy**: Restore deleted Python helpers and revert frontend filter format compilation.

---

## 10. Final Decision Matrix

| Component | FlexiRule Owns? | Reason / Authority |
| :--- | :---: | :--- |
| **Query UI** | **Yes** | FlexiRule supplies the rule canvas. |
| **Dynamic Values** | **Yes** | `ValueResolver` handles Jinja/variable replacements at runtime. |
| **Filter Compilation**| **No** (Frontend UI) | Compiled directly into valid native list-arrays in `QueryRecordsConfig.vue`. |
| **Child Joins** | **No** (Frappe) | Resolved automatically by Frappe's `DatabaseQuery` on execution. |
| **Permissions** | **No** (Frappe) | Evaluated natively inside `frappe.get_list` and match-conditions. |
| **SQL Generation** | **No** (Frappe) | Handled entirely by database drivers inside Frappe. |
| **Aggregation Execution**| **No** (Frappe) | Executed natively by passing aggregate SQL projections to `get_list`. |
