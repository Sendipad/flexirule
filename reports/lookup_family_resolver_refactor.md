# Lookup Resolver Family Architectural Refactor & Dynamic Link Report

## 1. Executive Summary

FlexiRule's Value Resolver architecture has been refactored to introduce a canonical **Lookup** family (`family: "lookup"`). The legacy standalone `"fetch"` resolver has been consolidated into the `"fetch"` operation under the **Lookup** family (`family: "lookup"`, `operation: "fetch"`).

In addition to static record lookups, the new architecture introduces native support for **Frappe Dynamic Links**, where the target DocType is determined dynamically at runtime from another field in the current document or child-table row (e.g. `party_type` -> `party`).

---

2. Canonical Schema & Configuration Contract

### Canonical Schema

The canonical resolver structure for record lookups is defined as:

```json
{
  "family": "lookup",
  "operation": "fetch",
  "kind": "lookup",
  "config": {
    "doctype_mode": "static" | "dynamic",
    "target_doctype": "Customer",
    "doctype_source": "party_type",
    "record_source_type": "doc_field" | "variable" | "expression",
    "record_field": "party",
    "fetch_field": "customer_group"
  }
}
```

### Modes

1. **Static Lookup (`doctype_mode = "static"`)**:
   - `target_doctype`: Fixed DocType string (e.g., `"Customer"`).
   - `record_field`: Field or path containing the record name/ID (e.g., `"customer"` or `"doc.customer"`).
   - `fetch_field`: Field to retrieve from the target document (e.g., `"customer_group"`).

2. **Dynamic Link Lookup (`doctype_mode = "dynamic"`)**:
   - `doctype_source`: Field or path specifying the target DocType (e.g., `"party_type"` or `"row.party_type"`).
   - `record_field`: Field or path containing the target record name/ID (e.g., `"party"` or `"row.party"`).
   - `fetch_field`: Field to retrieve from the dynamically resolved document.

---

3. Backward Compatibility & Normalization Pipeline

Full backward compatibility for legacy saved payloads (`kind: "fetch"`, `link_field`, `linked_doctype`, `fetch_field`) is maintained through dual-layer normalization:

### Backend Normalization (`ValueResolver.compile_resolver_config`)
Incoming legacy payloads specifying `kind: "fetch"` are automatically mapped into `LookupResolver(doctype_mode="static", target_doctype=linked_doctype, record_field=link_field, fetch_field=fetch_field)`. The legacy `FetchResolver` class remains available as an alias subclassing `LookupResolver`.

### Frontend Normalization (`useValueResolver.js`)
Saved configurations loaded into the UI are normalized into the canonical `{ family: "lookup", operation: "fetch", kind: "lookup", config: { ... } }` structure. The UI strategy registry maps `lookup` as the canonical strategy and hides legacy `fetch` strategy from strategy selector dropdowns.

---

4. Context & Child-Table Row Resolution

The backend `LookupResolver._resolve_scoped_value` helper respects contextual precedence when resolving fields:
1. If the field path starts with an explicit scope (`doc.`, `vars.`, `ctx.`, `loop.`, `row.`, `item.`, `caller.`, `rule.`), `get_context_value` evaluates the explicit path directly.
2. When no scope prefix is provided, and the resolver is evaluated in a child-table loop (`context["row"]` or `context["item"]`), `row`/`item` scope takes precedence before falling back to document scope (`doc.`).

Example:
Inside a child-table loop, `doctype_source = "party_type"` and `record_field = "party"` resolve `row.party_type` and `row.party`, correctly fetching fields for row-level Dynamic Links.

---

5. Smart Dynamic Link UI Auto-Detection

The `LookupResolver.vue` frontend component performs context-aware metadata inspection:
- When a user selects a source field (e.g., `party`), the component checks Frappe metadata for `fieldtype === "Dynamic Link"`.
- If the field is a Dynamic Link and its `options` metadata specifies the DocType field (e.g., `options = "party_type"`), the component automatically sets:
  - `doctype_mode = "dynamic"`
  - `doctype_source = "party_type"`
- If the field is a standard `Link` and its `options` metadata specifies a static DocType (e.g., `options = "Customer"`), the component pre-fills:
  - `doctype_mode = "static"`
  - `target_doctype = "Customer"`
- Users can toggle or override these settings at any time in the UI.

---

6. Security & Permission Boundaries

1. **DocType Validation**: The target DocType is validated against Frappe's metadata registry (`frappe.get_meta()`). If an invalid or fake DocType string is passed, the resolver returns `None`.
2. **Permission Check**: For non-Administrator user sessions, `LookupResolver` validates `frappe.has_permission(resolved_doctype, "read")`. If the user lacks read permissions for the target DocType, a `frappe.PermissionError` is raised.
3. **Safe Database Access**: Standard `frappe.db.get_value` is used without raw SQL, adhering strictly to FlexiRule's `SafeFrappeAPI` sandbox requirements.

---

7. Verification & Test Suite Results

The refactored Lookup family and Dynamic Link resolver have been verified via 14 unit tests in `flexirule/ruleflow/tests/test_fetch_resolver.py`:
- Static Lookups (`Customer` -> `customer_group`).
- Dynamic Link Lookups (`party_type = Customer` vs `party_type = Supplier`).
- Child Table Row Context (`row.party_type` / `row.party`).
- Missing source fields / invalid DocTypes / missing records.
- Permission enforcement for unauthorized users.
- Backward compatibility for legacy `kind: "fetch"` payloads.

All **440 tests** in the FlexiRule test suite pass successfully with zero errors or regressions.
