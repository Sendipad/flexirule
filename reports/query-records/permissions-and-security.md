# Permissions & Security Analysis

## 1. Overview of Security Architecture

FlexiRule's Query Records action enforces a dual-layer permission model:
1. **Default Layer**: Native Frappe Role & User Permission enforcement via `frappe.get_list()`.
2. **Override Guard Layer**: Controlled bypass of read permissions (`ignore_permissions`) protected by role checks, mandatory audit justifications, and security warning logging.

---

## 2. Standard Permission Enforcement Flow

When `ignore_permissions` is `0` (the default):
1. `execute()` calls `can_ignore_permissions(action, context, throw=True)` which returns `False`.
2. `_query_list()` calls `frappe.get_list(..., ignore_permissions=False)`.
3. Frappe's `DatabaseQuery` executes:
   - `self.check_read_permission(doctype)`: Throws `frappe.PermissionError` if the current session user lacks read rights for the DocType.
   - `build_match_conditions()`: Appends SQL `WHERE` conditions enforcing Frappe User Permissions (e.g. restricting sales users to their assigned territory/company).
   - `apply_fieldlevel_read_permissions()`: Removes restricted permlevel fields from the `SELECT` clause if the user lacks field-level read permissions.

---

## 3. Permission Bypass Architecture (`ignore_permissions`)

### Security Guard: `can_ignore_permissions()`
In `flexirule/ruleflow/core/permissions.py` (lines 160–210):

```python
def can_ignore_permissions(action, context=None, throw=True):
    if not int(getattr(action, "ignore_permissions", getattr(action, "skip_permissions", 0)) or 0):
        return False

    user = frappe.session.user
    user_roles = set(frappe.get_roles(user))
    allowed_roles = set(
        frappe.get_hooks("flexirule_ignore_permissions_roles")
        or frappe.get_hooks("flexirule_skip_permissions_roles")
        or []
    )
    if not allowed_roles:
        allowed_roles = set(DEFAULT_IGNORE_PERMISSIONS_ROLES) # {"System Manager"}

    if user != "Administrator" and not user_roles.intersection(allowed_roles):
        if throw:
            frappe.throw(
                _("ignore_permissions is restricted. Requires one of roles: {0}").format(
                    ", ".join(sorted(allowed_roles))
                ),
                frappe.PermissionError,
            )
        return False

    audit_reason = _extract_ignore_permissions_audit_reason(action)
    if not audit_reason:
        if throw:
            frappe.throw(
                _("ignore_permissions requires 'permission_audit_reason' in action configuration."),
                frappe.ValidationError,
            )
        return False

    frappe.logger("flexirule.security").warning(
        "ignore_permissions override by user=%s action=%s action_id=%s reason=%s",
        user, action.action_label, action.action_id, audit_reason,
    )
    return True
```

### Evaluation of Security Controls
1. **Role Gating**: Standard users cannot bypass permissions simply by saving a rule with `ignore_permissions: 1`. Unless the user possesses the `System Manager` role (or role in hook `flexirule_ignore_permissions_roles`), `can_ignore_permissions()` throws a `PermissionError` at execution time.
2. **Mandatory Audit Reason**: If `ignore_permissions` is set without a non-empty `permission_audit_reason`, execution throws `ValidationError`.
3. **Audit Logging**: Every execution with `ignore_permissions=True` writes a structured warning to the `flexirule.security` log channel containing session user, action ID, and reason.

---

## 4. SQL Injection & Input Sanitization Audit

### Filter & Field Validation
Before executing a query, `QueryRecordsHandler` runs `_validate_doctype_field_references()`:
- Verifies that target DocTypes exist via `frappe.get_meta()`.
- Validates field names using `_is_plain_field_reference()` (rejects illegal characters, SQL keywords, and unescaped functions).
- Verifies that filter fields exist on the target or child DocType schemas.

### SQL Parameterization
- Filter values are passed as parameterized arguments to `frappe.get_list()`, preventing SQL injection.
- Expressions inside filter values are parsed through AST-based `SafeEvalVisitor`, prohibiting dunder access (`__import__`, `__subclasses__`) and import statements.
