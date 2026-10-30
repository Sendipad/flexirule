# FlexiRule Frappe v15 / v16 Query Compatibility Deliberation

**Context:** Live, unscripted operational war room dialogue transcribing the architectural strategy to adapt FlexiRule's condition evaluation and query building across Frappe v15 and v16.

---

## Specialist Introduction

**The Specialist Expert:**
"Before anyone proposes a single line of Python, we must establish the foundational mechanics of Frappe Framework's query engine evolution between v15 and v16.

In **Frappe v15**, `frappe.qb.get_query` relies on `Engine.get_query()`. Crucially:
1. **Permission Enforcement:** `Engine.get_query` in v15 does *not* accept `ignore_permissions`. If an application calls `frappe.qb.get_query("DocType")` without passing pre-built permission criteria, no user-level read permissions are automatically appended at the SQL AST layer.
2. **Logical Filter Parsing:** `frappe.qb.get_query` in v15 accepts simple list filters (`[["status", "=", "Open"]]`), but fails or misinterprets complex boolean tree structures involving arbitrary `OR` grouping or nested list trees (`[["status", "=", "Open"], "or", ["priority", "=", "High"]]`).
3. **Nested Set Operators:** Tree DocType operators (`descendants of`, `ancestors of`, etc.) are resolved in `frappe.database.query.get_nested_set_hierarchy_result`, but in v15, mixing boolean tree structures with tree operators causes native filter parsing to fail or raise unexpected syntax exceptions.

In **Frappe v16**:
1. `Engine.get_query` explicitly accepts `ignore_permissions: bool`. When `ignore_permissions=False`, Frappe natively resolves `frappe.has_permission` and appends user/role permission criteria directly into the PyPika AST.
2. `Engine.get_query` natively supports recursive boolean group parsing (`_parse_nested_filters` / `_compile_logical_filters`), making custom AST group assembly redundant on v16.

**Architectural Directives for FlexiRule:**
- **Zero Version Checking via Strings:** Never use fragile string comparisons on `frappe.__version__` (e.g., `frappe.__version__.startswith("15")`), as pre-release tags (`16.0.0-dev`, `15.x.x`), custom forks, or backported patches break string comparisons.
- **Feature Capability Detection at Module Import:** Inspect the signature of `Engine.get_query` at import time (`inspect.signature(Engine.get_query)`). Cache the capability object immutably.
- **Fail Closed Security:** If `ignore_permissions=False` is requested on v15 where native Query Builder permissions cannot be enforced, raise a `frappe.ValidationError` unless the caller explicitly opts into an audited permission bypass (`skip_permissions=1` / `ignore_permissions=1`) with a non-empty `permission_audit_reason`.
- **Pure AST Delegation:** Wrap v15 fallback logic strictly inside `flexirule.ruleflow.utils.frappe_query_compat` so that high-level rule action handlers (`QueryRecordsHandler`, `ConditionCompiler`) execute clean, version-agnostic code."

---

## Round 1: Initial Proposal & Critique

### The Engineer
"Here is our initial proposal for `frappe_query_compat.py`:

```python
from dataclasses import dataclass
from inspect import signature
import frappe
from pypika import Criterion
from frappe.database.operator_map import OPERATOR_MAP
from frappe.database.query import Engine, get_nested_set_hierarchy_result

@dataclass(frozen=True)
class FrappeQueryCapabilities:
    supports_ignore_permissions: bool

def detect_query_capabilities() -> FrappeQueryCapabilities:
    try:
        get_query = getattr(Engine, "get_query", None)
        params = signature(get_query).parameters if callable(get_query) else {}
    except Exception:
        params = {}
    return FrappeQueryCapabilities(
        supports_ignore_permissions="ignore_permissions" in params,
    )

QUERY_CAPABILITIES = detect_query_capabilities()

def execute_query(doctype: str, kwargs: dict, ignore_permissions: bool):
    query_kwargs = dict(kwargs)
    filters = query_kwargs.get("filters")

    if QUERY_CAPABILITIES.supports_ignore_permissions:
        query_kwargs["ignore_permissions"] = ignore_permissions
    else:
        if not ignore_permissions:
            raise frappe.ValidationError("Permission enforcement not supported on Query Builder in v15")
        if _contains_logical_filter_groups(filters):
            query_kwargs["filters"] = _compile_logical_filters(doctype, filters)

    query = frappe.qb.get_query(doctype, **query_kwargs)
    return query.run(as_dict=True)
```

We detect `ignore_permissions` parameter in `Engine.get_query`. On v16, we pass `ignore_permissions` directly. On v15, if `ignore_permissions=False`, we raise a `ValidationError`. If `filters` contain logical `AND`/`OR` groups, we compile them into PyPika `Criterion` objects before passing them to `frappe.qb.get_query`."

### The Devil's Advocate
"That proposal has serious holes!
1. **Silent Permission Leak on v15:** You raise a `ValidationError` if `ignore_permissions=False`, but what if a user rule runs on v15 with `skip_permissions=1`? You strip `ignore_permissions` from `query_kwargs` and run `frappe.qb.get_query`. But does `frappe.qb.get_query` apply *any* security filtering? No! In v15, `get_query` returns ALL records across tenants or restricted roles. If the caller didn't pass explicit permission filters, you've turned a rule execution into an unauthorized data leak!
2. **Nested Set Breakdown:** What happens when a v15 `_compile_logical_filters` receives a tree operator like `["parent_item", "descendants of", "Group-A"]` nested inside an `OR` group? `OPERATOR_MAP` in v15 does NOT contain `"descendants of"` directly—it stores `nested_set` as a key. Your `_criterion_for_leaf` will crash with `KeyError: 'descendants of'`!
3. **Double Wildcard Corruption:** How are string operators like `starts with` or `like` handled when compiled into PyPika criteria on v15 vs passed as raw filters on v16? If `_normalize_filters_for_backend` adds `%` wildcards and then `OPERATOR_MAP['starts with']` appends `%` again, query matching will fail!"

### The Lazy Developer / End-User
"I don't care about PyPika AST internal details or whether my bench runs v15 or v16. I want to build a rule on v15, export the rule JSON, import it into a v16 server, and have it work with EXACTLY zero configuration changes!
- Why should I have to rewrite my query filters when upgrading to v16?
- If I use single leaf filters, why does `execute_query` expect a list of lists while canonical tree builders emit a single tuple `("doctype", "field", "=", "val")`?
- If `frappe.qb.get_query` in v15 raises an error because of missing permission checks, does FlexiRule force me to switch to `frappe.get_list`? Because `frappe.get_list` returns different dict structures and doesn't support complex PyPika SQL aggregations (`Count`, `Sum`, `Avg`)!"

---

## Round 2: Stress-Test & Second-Order Effects

### The Specialist Expert
"Let's resolve the critical second-order flaws exposed in Round 1:

1. **Permission Architecture Enforcement (v15 vs v16):**
   - On **v16**: Pass `ignore_permissions=ignore_permissions` natively to `frappe.qb.get_query`.
   - On **v15**: `frappe.qb.get_query` cannot enforce user permissions natively. FlexiRule's permission policy mandates that background/rule queries operating with `ignore_permissions=False` must NOT silently execute without permission checks. Therefore:
     - On v15, if `ignore_permissions=False`, fail closed immediately with `frappe.ValidationError` instructing the user to enable 'Skip Permissions' with a required `permission_audit_reason`.
     - We strictly **refuse** to fall back to `frappe.get_list` on v15. Why? Because `frappe.get_list` has a different API surface (different join handling, lack of raw PyPika function selection, different group-by syntax). Maintaining dual query paths (`get_list` vs `get_query`) would introduce subtle semantic bugs across versions.

2. **Nested Set Operator Resolution in Logical Groups:**
   - In v15, nested-set operators (`descendants of`, `ancestors of`, `not descendants of`, `not ancestors of`) are handled via `get_nested_set_hierarchy_result(doctype, target, operator)`.
   - When compiling legacy `Criterion` for v15, `_criterion_for_nested_set_leaf` must invoke `get_nested_set_hierarchy_result`, convert the returned boundary names into an `in` or `not in` list, and map that through `OPERATOR_MAP["in"]`.
   - On **v16**, when native logical group parsing is active, tree operators inside logical groups must be rewritten via `_expand_nested_set_filters` to equivalent `in` / `not in` tuple criteria before hitting `frappe.qb.get_query`, because v16's native boolean group parser classifies simple conditions using `OPERATOR_MAP` and does not recognize `NestedSetHierarchy` enum strings inside boolean group branches.

3. **Single Leaf Normalization:**
   - Canonical condition evaluators and simple Fetch Records configurations may pass a single filter tuple `["doctype", "field", "=", "val"]`.
   - On both v15 and v16, `execute_query` must normalize a single filter tuple into a list of list rows `[["doctype", "field", "=", "val"]]` when no logical connector tokens (`and`/`or`) are present, ensuring native `frappe.qb.get_query` never receives an unnested 1D tuple."

### The Devil's Advocate
"Let's stress-test edge cases:
- **Performance Overhead of Signature Inspection:** Is `signature(Engine.get_query)` being called on every query execution? If a rule executes 10,000 times in a batch, calling `inspect.signature` 10,000 times will destroy performance!
- **Mixed AND/OR Connectors at the Same Level:** What if a user inputs `[["status", "=", "Open"], "or", ["priority", "=", "High"], "and", ["docstatus", "=", 0]]` without explicit parenthetical sub-grouping?
- **Linked / Child Table Fields in v15 PyPika Criteria:** If a v15 logical group filter contains `["Child Doctype", "qty", ">", 10]`, can `_criterion_for_leaf` compile it? No! `frappe.qb.DocType(doctype)` only references the parent table. Referencing a child table field without an explicit PyPika join will produce invalid SQL like `tabParent.qty > 10`!"

### The Engineer
"We address all three stress-test points as follows:
1. **Zero Hot-Path Overhead:** `QUERY_CAPABILITIES` is evaluated **once** at module import time (`QUERY_CAPABILITIES = detect_query_capabilities()`). Zero runtime inspection on query execution.
2. **Strict Validation of Mixed Connectors:** If `_compile_logical_filters` detects mixed `and` and `or` connectors at the same list depth without explicit nesting, it raises `frappe.ValidationError("Mixed AND/OR operators at the same level require an explicit nested filter group")`.
3. **Scope Bounding for v15 PyPika Groups:** Logical group compilation on v15 is explicitly bounded to root DocType fields. If a leaf references a field with `.` (e.g. `roles.role`) or a child table, `_criterion_for_leaf` raises `frappe.ValidationError` explaining that child/linked filter groups on v15 require upgrading to v16 or using simple flat filters. This preserves strict correctness without attempting fragile table-join guessing in v15."

### The Lazy Developer / End-User
"That guarantees:
1. Rule definitions are 100% identical across v15 and v16.
2. If a query is invalid on v15, I get a clear, actionable `ValidationError` upfront, not a silent SQL syntax failure or security leak.
3. On v16, my app automatically leverages native `ignore_permissions` and native group parsing without changing any code or settings."

---

## The Maestro Phase (Final Decision)

**The Maestro:**
"The deliberation is complete. All edge cases, security implications, and version-drift risks have been thoroughly resolved through feature detection, strict fail-closed security, single-leaf normalization, and bounded PyPika AST compilation.

Here is the comprehensive, production-ready implementation solution for `flexirule/ruleflow/utils/frappe_query_compat.py`."
