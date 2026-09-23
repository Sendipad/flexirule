# Security Audit: Value Resolver Subsystem

## Overview

The Value Resolver subsystem evaluates user-configured expressions during rule execution. Because expressions can reference document fields, variables, and Python utilities, strict security boundaries are necessary to prevent:
1. **Server-Side Template Injection (SSTI)** in Jinja rendering.
2. **Arbitrary Code Execution / AST Escapes** in Python expression evaluation.
3. **Unauthorized Database Access** via database fetch operations.
4. **Enforcement Bypasses** of configured resolver security levels.

---

## Security Analysis of Execution Components

### 1. Python Expression Evaluation (`SafeEvalResolver` / `_safe_eval`)
- **Mechanism**: Executed via `_safe_eval(expression, context)` in action handlers.
- **AST Inspection**: Uses `SafeEvalVisitor` (`ast.NodeVisitor`) defined in `flexirule/ruleflow/core/permissions.py`.
- **Enforced Restrictions**:
  - Blocks dangerous dunder attributes: `__subclasses__`, `__class__`, `__bases__`, `__mro__`, `__import__`, `__globals__`, `__builtins__`.
  - Blocks import statements (`import`, `from ... import`).
  - Restricts available globals to safe built-ins, `frappe.utils`, and `SafeFrappeAPI`.
- **Verdict**: **SAFE**. Known sandbox escapes (e.g. `FR-SEC-001`) are verified as blocked by regression tests in `test_audit_reproductions.py`.

---

### 2. Jinja Rendering (`JinjaResolver`)
- **Mechanism**: Renders strings containing `{{` or `{%` via `frappe.render_template(template, context)`.
- **Context Sanitization**: Context is generated via `ActionHandler._build_template_context(context)`:
  - Raw `frappe` module access is **EXCLUDED** from the rendering context.
  - Only safe helper methods (e.g. `frappe.utils.nowdate`, `frappe.utils.flt`) are exposed.
- **Verdict**: **SAFE**. Mitigates Jinja SSTI exploits (e.g. `FR-SEC-002`).

---

### 3. Database Access (`FetchResolver`)
- **Mechanism**: `FetchResolver` executes `frappe.db.get_value(linked_doctype, link_value, fetch_field)`.
- **Input Sanitization**:
  - `linked_doctype`, `link_value`, and `fetch_field` are passed as parameterized parameters to Frappe's query engine.
  - Prevents SQL injection.
- **Scope**: Single field scalar reads. No arbitrary SQL queries or mutations (`db_set_value`, `delete`, `insert`) are allowed.
- **Verdict**: **SAFE**.

---

### 4. Level Restriction Enforcement Gap (`VR-AUDIT-001`)
- **Mechanism**: The setting `resolverLevel` (`basic`, `standard`, `advanced`, `full`) restricts allowed formula categories.
- **Vulnerability**: Enforcement exists **ONLY in Vue JS** (`FlexValueControl.vue` via `RESOLVER_LEVEL_KIND_MAP` and `allowedBuilderKinds`).
- **Impact**: The backend `ValueResolver.compile()` does NOT check `resolverLevel`. An attacker or API client submitting a custom JSON payload can execute `advanced` resolvers (e.g., `math_formula` or `child_aggregation`) on a site configured for `basic` resolver level.
- **Severity**: **MEDIUM / HIGH** (Security boundary mismatch).

---

### 5. Fallback Expression Execution Risk (`VR-AUDIT-002`)
- **Mechanism**: When `config` is omitted from a `resolverToken` or `mode: "resolver"` object, `ValueResolver.compile()` falls back to `SafeEvalResolver` on the `expression` or `value` string.
- **Impact**: While `SafeEvalResolver` applies AST sanitization, fallback to freeform Python string evaluation bypasses structured builder validation.
- **Severity**: **MEDIUM**.
