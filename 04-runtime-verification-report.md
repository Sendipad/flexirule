# Audit Report 04: Runtime & Security Verification

## 1. Permission Boundaries
FlexiRule enforces strict role-based access for execution.
- **skip_permissions:** Only users with "System Manager" role can save rules with this flag enabled.
- **Verification:** Attempted to save a rule with `skip_permissions=1` as a "Rule Builder" user. Request blocked with `PermissionError` by `Rule.validate`.

## 2. Document Safety
Rules running in `Before Save` or `Validate` are wrapped in the main database transaction.
- **Finding:** If a Rule raises an error (via `Stop (Error)` or `Raise Error`), the entire document save is rolled back. This is the desired behavior for validation rules.
- **Side Effect Risk:** Any `Notify (Email)` actions triggered *before* the error will still be enqueued in the Background Jobs table, although the email itself won't send until the transaction commits (Frappe standard).

## 3. Safe API Proxy
The `SafeFrappeAPI` in `engine.py` restricts Jinja/Python conditions to read-only operations.
- **Blocked:** `frappe.db.set_value`, `frappe.delete_doc`, `frappe.db.sql`.
- **Allowed:** `frappe.get_all`, `frappe.get_value`, `frappe.db.exists`.
- **Verification:** Verified that attempting to call `doc.save()` inside a condition block raises a `PermissionError`.
