# Security Audit — FlexiRule

## 1. Attack Surface & Threat Model

FlexiRule allows users with the `Rule Builder` role to configure executable workflow logic. Treat all rule configuration data (expressions, field mappings, templates, process calls) as potentially untrusted user input.

Primary security boundaries audited:
1. **Python Expression Sandbox**: `frappe.safe_eval`, `runtime_eval.py`, `compiler.py`.
2. **Template Rendering Engine**: `document_action.py`, `simple_actions.py` (Jinja template injection surface).
3. **Restricted Frappe API Proxy**: `SafeFrappeAPI` in `engine.py`.
4. **Whitelisted Method Dispatch**: `check_method_permission()` in `permissions.py`.
5. **Permission Override Controls**: `can_ignore_permissions()` and `ignore_permissions` audit reasons in `permissions.py`.

---

## 2. Security Findings

### Finding FR-SEC-001 (CRITICAL) — Sandbox Escape via Stubbed AST Validation in `validate_safe_eval`
- **File**: `flexirule/ruleflow/core/permissions.py`
- **Function/Class**: `validate_safe_eval`
- **Description**: `validate_safe_eval` performs no AST validation, enabling Python sandbox escape inside `frappe.safe_eval`.
- **Technical Analysis**:
  ```python
  def validate_safe_eval(expression):
      try:
          compile(expression, "<string>", "eval")
      except SyntaxError as e:
          frappe.throw(_("Invalid syntax in expression: {0}").format(str(e)), frappe.ValidationError)
      return True  # Expression is safe
  ```
  The function checks only Python syntax via `compile()`. It does not inspect the Abstract Syntax Tree (AST) for prohibited attributes, method calls, or dunder references.

  **Proof of Concept Payload**:
  A Rule Builder user can save a condition expression such as:
  ```python
  (lambda fc: [c for c in fc.__subclasses__() if c.__name__ == 'BuiltinImporter'][0]().load_module('os').system('id'))(object)
  ```
  Because `validate_safe_eval` returns `True`, `frappe.safe_eval` or custom evaluators execute this code, permitting remote code execution (RCE) on the underlying server.
- **Impact**: Critical Remote Code Execution (RCE) / Full System Compromise.
- **Remediation**: Implement strict AST node visitor checks using `ast.parse()` to disallow dunder attribute access (`__subclasses__`, `__class__`, `__globals__`, `__import__`), function definitions, and unsafe AST node types prior to evaluation.

---

### Finding FR-SEC-002 (CRITICAL) — Unsanitized Server-Side Template Injection (SSTI) in Document Actions
- **File**: `flexirule/ruleflow/core/action_handlers/document_action.py`
- **Function/Class**: `DocumentActionHandler._render_scalar`
- **Description**: Unfiltered template strings are passed directly to `frappe.render_template`.
- **Technical Analysis**:
  ```python
  def _render_scalar(self, value, context):
      if value is None or not isinstance(value, str):
          return value
      return frappe.render_template(value, self._template_context(context))
  ```
  `_template_context(context)` passes `{"frappe": context.get("frappe") or frappe}` into the Jinja rendering context. An attacker with Rule Builder permissions can inject arbitrary Jinja2 statements in `description` or `comment_text`:

  **Proof of Concept Payload**:
  ```jinja
  {{ frappe.db.sql("SELECT password FROM tabUser WHERE name='Administrator'") }}
  ```
  When executed, `frappe.render_template` executes the arbitrary SQL query with System Manager database privileges, exposing sensitive user credentials.
- **Impact**: Critical Data Exposure / Arbitrary SQL Execution / Privilege Escalation.
- **Remediation**: Do not pass the raw `frappe` module into Jinja contexts. Use `frappe.utils.safe_eval` or a restricted Jinja environment without object method access.

---

### Finding FR-SEC-003 (HIGH) — SafeFrappeAPI Method Execution Bypass via `format_value`
- **File**: `flexirule/ruleflow/core/engine.py`
- **Function/Class**: `SafeFrappeAPI.format_value`
- **Description**: Exposes `frappe.format_value` without field metadata parameter sanitization.
- **Technical Analysis**:
  ```python
  @staticmethod
  def format_value(value, df=None, doc=None, currency=None):
      return frappe.format_value(value, df, doc, currency)
  ```
  `frappe.format_value` accepts a dictionary or DocField object `df`. If `df` defines a custom Python formatter or fieldtype options, Frappe dynamically imports and invokes the formatter via `frappe.get_attr`. An attacker can pass a crafted dictionary as `df` (e.g. `{"fieldtype": "Currency", "options": "os.system"}`) to execute arbitrary python methods.
- **Impact**: Sandbox bypass leading to code execution.
- **Remediation**: Validate that `df` is a genuine `DocField` instance fetched from `frappe.get_meta()`, rejecting dict overrides.

---

### Finding FR-SEC-004 (HIGH) — Background Job Session User Permission Bypass in `can_ignore_permissions`
- **File**: `flexirule/ruleflow/core/permissions.py`
- **Function/Class**: `can_ignore_permissions`
- **Description**: Asynchronous execution defaults `frappe.session.user` to `Administrator`.
- **Technical Analysis**: `can_ignore_permissions` checks `frappe.session.user`. In background workers (`frappe.enqueue`), `frappe.session.user` defaults to `Administrator`. If an action with `ignore_permissions=1` is executed asynchronously by a low-privileged user, the background worker evaluates `user = "Administrator"` and bypasses the role check entirely.
- **Impact**: Unauthorized permission bypass during background processing.
- **Remediation**: Preserve `executed_by` session user in background job payloads and pass explicit `user` into `can_ignore_permissions(action, user=executed_by)`.
