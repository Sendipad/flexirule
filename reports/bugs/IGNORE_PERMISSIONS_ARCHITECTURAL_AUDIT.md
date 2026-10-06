# Architectural Audit & Strategic Analysis: `ignore_permissions` in FlexiRule

**Document Version:** 1.0.0
**Target Subsystem:** FlexiRule Engine (`flexirule`)
**Scope:** Action Types, Security Model, Permission Propagation, Execution Contexts, Frappe Framework Integration
**Status:** Comprehensive Architectural Analysis (RC Pre-Release Audit)

---

## 1. Executive Summary

`ignore_permissions` in FlexiRule is a sensitive privilege-override mechanism designed to allow authorized business rules to bypass standard Frappe DocType and field-level permission checks during rule execution.

Currently, `ignore_permissions` is defined as an ad-hoc Check field on the `Rule Action` DocType (`flexirule/ruleflow/doctype/rule_action/rule_action.json`). The current architecture exhibits several design inconsistencies, contract mismatches, and execution context gaps:

1. **Over-Broad and Ambiguous Schema Placement**: `ignore_permissions` exists at the generic `Rule Action` child DocType level. However, only 3 out of 13 registered Action Types (`Document Action`, `Query Records`, and `Sub-Rule`) implement backend checks for it. For the remaining 10 Action Types, the setting is either silently ignored or semantically non-applicable.
2. **Hardcoded Frontend Configuration Contracts**: In the Vue 3 Rule Builder, `ignore_permissions` and its companion `permission_audit_reason` are explicitly hardcoded into three specific component panels (`DocumentActionConfig.vue`, `QueryRecordsConfig.vue`, and `Sub-RuleConfig.vue`). Standard components (`ConfigurationPanel.vue`, `ActionSettings.vue`, `contracts.js`) do not expose or register `ignore_permissions` uniformly, creating contract drift between the backend action registry and the frontend graph builder.
3. **Implicit vs. Explicit Permission Bypasses**: Internal operations in `simple_actions.py` (e.g., `Notify` creating system notifications via `.insert(ignore_permissions=True)`) and system maintenance helpers (such as `process_sync.py`, `process_registry.py`, `rule_service.py`) unilaterally force `ignore_permissions=True` hardcoded at the backend level. This obscures whether permission bypasses are driven by author-configured policies or implicit system-level operations.
4. **Context Blindness in Execution Paths**: The guard `can_ignore_permissions()` validates `frappe.session.user` against permitted roles (defaulting to `System Manager`). In background queue execution (e.g., `rq` background tasks) or scheduled jobs, `frappe.session.user` defaults to `"Administrator"` or `"Guest"`, causing security policy enforcement to behave differently depending on whether the rule was triggered synchronously or asynchronously.
5. **Architectural Recommendation**: `ignore_permissions` must not be treated as a generic `Rule Action` top-level DocType field. It should be refactored into an **Action-Type-Specific Capabilities & Settings Property** (`Option B / Option D Hybrid`), exposed strictly through canonical Action Type contracts (`contracts.py` / `contracts.js`) and enforced by a centralized Execution Context Security Coordinator.

---

## 2. Complete Usage Inventory

Below is the exhaustive inventory of all source-code occurrences of `ignore_permissions` across the repository (excluding unit test files and `__pycache__`).

| File Path                                                    | Function / Class                             | Category                  | Current Purpose / Flow                                                                                                                      |
| :----------------------------------------------------------- | :------------------------------------------- | :------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------ |
| `flexirule/ruleflow/doctype/rule_action/rule_action.json`    | Field Definition                             | DocType Metadata          | Defines `ignore_permissions` (Check) and `permission_audit_reason` (Small Text) as fields on `Rule Action`.                                 |
| `flexirule/ruleflow/core/permissions.py`                     | `can_ignore_permissions()`                   | Governance / Security     | Validates user role against allowed hooks/defaults and requires non-empty `permission_audit_reason`.                                        |
| `flexirule/ruleflow/core/permissions.py`                     | `_extract_ignore_permissions_audit_reason()` | Governance / Security     | Reads audit reason from `action.permission_audit_reason` or `action.config.permission_audit_reason`.                                        |
| `flexirule/ruleflow/core/action_handlers/document_action.py` | `DocumentActionHandler.execute()`            | Runtime Consumption       | Calls `can_ignore_permissions()`, passes flag to `_create_new`, `_update_existing`, `_delete_record`, `_create_todo`, `_add_comment`.       |
| `flexirule/ruleflow/core/action_handlers/document_action.py` | `_create_new()`                              | Frappe API Pass-Through   | Passes `ignore_permissions` to `frappe.get_doc().insert(ignore_permissions=...)`.                                                           |
| `flexirule/ruleflow/core/action_handlers/document_action.py` | `_update_existing()`                         | Frappe API Pass-Through   | Checks `frappe.has_permission(doctype, "write")` if `not ignore_permissions`, then calls `doc.save(ignore_permissions=...)`.                |
| `flexirule/ruleflow/core/action_handlers/document_action.py` | `_delete_record()`                           | Frappe API Pass-Through   | Checks `frappe.has_permission(doctype, "delete")` if `not ignore_permissions`, then calls `frappe.delete_doc(..., ignore_permissions=...)`. |
| `flexirule/ruleflow/core/action_handlers/document_action.py` | `_create_todo()`, `_add_comment()`           | Frappe API Pass-Through   | Calls `todo.insert(ignore_permissions=...)` and `comment.insert(ignore_permissions=...)`.                                                   |
| `flexirule/ruleflow/core/action_handlers/query_records.py`   | `QueryRecordsHandler.execute()`              | Runtime Consumption       | Calls `can_ignore_permissions()`, passes flag to list, doc, count, aggregate, group_by, and exist queries.                                  |
| `flexirule/ruleflow/core/action_handlers/query_records.py`   | `_query_list()`                              | Frappe API Pass-Through   | Passes `"ignore_permissions": ignore_permissions` to `frappe.get_list()` / `frappe.get_all()`.                                              |
| `flexirule/ruleflow/core/action_handlers/query_records.py`   | `_query_doc()`                               | Frappe API Pass-Through   | Checks `frappe.has_permission(doctype, "read")` if `not ignore_permissions`, then calls `frappe.get_doc()`.                                 |
| `flexirule/ruleflow/core/action_handlers/query_records.py`   | `_query_report()`                            | Execution Gap             | Contains comment: _"Note: ignore_permissions is a no-op for Query Report mode"_.                                                            |
| `flexirule/ruleflow/core/action_handlers/sub_rule.py`        | `SubRuleHandler.execute()`                   | Runtime Consumption       | Evaluates `can_ignore_permissions()`, logs execution, and sets isolated sub-rule execution flags.                                           |
| `flexirule/ruleflow/core/action_handlers/simple_actions.py`  | `NotifyHandler.execute()`                    | Implicit Hardcoded Bypass | Hardcodes `notification.insert(ignore_permissions=True)` without checking Action configuration.                                             |
| `flexirule/ruleflow/core/graph_service.py`                   | `serialize_rule()`                           | Serialization             | Extracts `ignore_permissions` from `Rule Action` doc and includes it in JSON graph payload.                                                 |
| `flexirule/ruleflow/core/process_sync.py`                    | `sync_process()`                             | Engine Infrastructure     | Forces `doc.flags.ignore_permissions = True` on internal Process document inserts.                                                          |
| `flexirule/ruleflow/core/process_registry.py`                | `register_process()`                         | Engine Infrastructure     | Forces `ignore_permissions=True` on internal process registration writes.                                                                   |
| `flexirule/ruleflow/core/rule_service.py`                    | `create_rule()`                              | Engine Infrastructure     | Forces `new_doc.insert(ignore_permissions=True)` during programmatic rule creation.                                                         |
| `flexirule/public/js/.../DocumentActionConfig.vue`           | Template & Validation                        | Frontend UI               | Renders `ignore_permissions` Checkbox and `permission_audit_reason` Small Text control.                                                     |
| `flexirule/public/js/.../QueryRecordsConfig.vue`             | Template & Validation                        | Frontend UI               | Renders `ignore_permissions` Checkbox and `permission_audit_reason` Small Text control.                                                     |
| `flexirule/public/js/.../SubRuleConfig.vue`                  | Template & Validation                        | Frontend UI               | Renders `ignore_permissions` Checkbox and `permission_audit_reason` Small Text control.                                                     |
| `flexirule/public/js/.../useRuleStore.js`                    | Graph Normalization                          | State Management          | Maps `ignore_permissions: node.data?.ignore_permissions ?? node.data?.skip_permissions ?? 0`.                                               |
| `flexirule/public/js/.../useGraphStore.js`                   | Graph Normalization                          | State Management          | Maps `ignore_permissions: action.ignore_permissions ?? action.skip_permissions ?? 0`.                                                       |
| `flexirule/public/js/.../useRuleConfig.js`                   | Graph Validation                             | Form Validation           | Validates that `permission_audit_reason` is non-empty when `ignore_permissions` is true.                                                    |
| `flexirule/patches/migrate_skip_permissions.py`              | Migration Patch                              | Schema Migration          | Copies legacy `skip_permissions` values to `ignore_permissions`.                                                                            |

---

## 3. Action Type Matrix

The repository contains **13 registered Action Types**. The matrix below establishes the relationship between each Action Type, its current UI/Backend behavior, runtime consumption, Frappe API interaction, and architectural assessment.

| Action Type         | Has Field in DocType? | UI Exposes It?                   | Backend Accepts It?        | Runtime Consumes It?        | Frappe API Receives It?                              | Assessment & Status                                                                                |
| :------------------ | :-------------------- | :------------------------------- | :------------------------- | :-------------------------- | :--------------------------------------------------- | :------------------------------------------------------------------------------------------------- |
| **Document Action** | Yes (DocType level)   | Yes (`DocumentActionConfig.vue`) | Yes (`document_action.py`) | Yes (`execute()`)           | Yes (`insert`, `save`, `delete_doc`)                 | **Correctly Implemented**, but needs contract-driven UI rendering instead of custom Vue templates. |
| **Query Records**   | Yes (DocType level)   | Yes (`QueryRecordsConfig.vue`)   | Yes (`query_records.py`)   | Yes (`execute()`)           | Yes (`get_list`, `get_all`, `get_doc`)               | **Partially Correct**. `Query Report` mode within Query Records silently ignores it.               |
| **Sub-Rule**        | Yes (DocType level)   | Yes (`SubRuleConfig.vue`)        | Yes (`sub_rule.py`)        | Yes (`execute()`)           | Indirectly (sub-rule context)                        | **Correctly Implemented** for cascading execution context.                                         |
| **Assignment**      | Yes (DocType level)   | No (Hidden by UI logic)          | No                         | No                          | No                                                   | **Unnecessarily Exposed** at DocType level; unused by handler (`assignment.py`).                   |
| **Condition**       | Yes (DocType level)   | No                               | No                         | No                          | No                                                   | **Unnecessarily Exposed** at DocType level; pure logic evaluation (`condition.py`).                |
| **Process**         | Yes (DocType level)   | No                               | No                         | No                          | No                                                   | **Unnecessarily Exposed** at DocType level; delegates to custom process scripts (`process.py`).    |
| **Notify**          | Yes (DocType level)   | No                               | No                         | Hardcoded `True` in handler | Yes (`notification.insert(ignore_permissions=True)`) | **Incorrect / Hidden Implicit Bypass**. Always bypasses permissions regardless of user config.     |
| **Raise Error**     | Yes (DocType level)   | No                               | No                         | No                          | No                                                   | **Unnecessarily Exposed** at DocType level; terminal control flow (`simple_actions.py`).           |
| **Stop**            | Yes (DocType level)   | No                               | No                         | No                          | No                                                   | **Unnecessarily Exposed** at DocType level; terminal node (`simple_actions.py`).                   |
| **Wait**            | Yes (DocType level)   | No                               | No                         | No                          | No                                                   | **Unnecessarily Exposed** at DocType level; delay node (`simple_actions.py`).                      |
| **Loop**            | Yes (DocType level)   | No                               | No                         | No                          | No                                                   | **Unnecessarily Exposed** at DocType level; graph control flow (`loop.py`).                        |
| **Switch**          | Yes (DocType level)   | No                               | No                         | No                          | No                                                   | **Unnecessarily Exposed** at DocType level; branching control flow (`switch.py`).                  |
| **Entry Action**    | Yes (DocType level)   | No                               | No                         | No                          | No                                                   | **Unnecessarily Exposed** at DocType level; start node (`simple_actions.py`).                      |

---

## 4. Frontend Analysis

### 4.1 UI Configuration Locations

In the Vue 3 Rule Builder frontend, `ignore_permissions` is configured inside specific Action Config panel components:

- `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/DocumentActionConfig.vue`
- `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue`
- `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/SubRuleConfig.vue`

In each of these components, the setting is rendered using a `FrappeControl` component bound to `fieldname: 'ignore_permissions'`, accompanied by a conditional `permission_audit_reason` input field:

```html
<FrappeControl
	:df="{
    fieldname: 'ignore_permissions',
    fieldtype: 'Check',
    label: __('Ignore Permissions'),
    description: __('Bypass standard Frappe permission checks for this action')
  }"
	:modelValue="node?.data?.ignore_permissions"
	@update:modelValue="(val) => update_action_key('ignore_permissions', val)"
/>
```

### 4.2 Frontend Contract & Schema Mismatches

1. **Hardcoded Visibility**: Instead of reading Action Type contracts from `flexirule/public/js/flexirule/core/contracts.js` or fetching backend contracts dynamically, the Vue frontend hardcodes the rendering of `ignore_permissions` in specific `.vue` templates.
2. **Generic Fallbacks**: In `ActionSettings.vue` and `ConfigurationPanel.vue`, fields from the `Rule Action` DocType are listed. Because `ignore_permissions` is a child DocType field on `Rule Action`, it technically exists in the schema for _every_ action node, even though components like `AssignmentConfig.vue`, `LoopConfig.vue`, and `NotifyConfig.vue` ignore it.
3. **Legacy Fallback Mapping**: Both `useRuleStore.js` and `useGraphStore.js` perform fallback resolution:
   `ignore_permissions: node.data?.ignore_permissions ?? node.data?.skip_permissions ?? 0`
   This is preserved for backwards compatibility with historical JSON fixtures (`rule_sample.json`), despite `skip_permissions` being deprecated.

---

## 5. Backend Analysis

### 5.1 Validation & Normalization Architecture

In `flexirule/ruleflow/core/permissions.py`, `can_ignore_permissions(action, context=None, throw=True)` acts as the gatekeeper for permission bypass:

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
        allowed_roles = set(DEFAULT_IGNORE_PERMISSIONS_ROLES) # System Manager

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
        user,
        getattr(action, "action_label", None) or getattr(action, "name", None),
        getattr(action, "action_id", None),
        audit_reason,
    )
    return True
```

### 5.2 Discovered Backend Architectural Inconsistencies

1. **Contract Disconnect**: `BaseActionHandler.get_action_contract()` (`flexirule/ruleflow/core/action_handlers/base_contract.py`) defines default metadata properties (`required_fields`, `has_next_true`, `terminal`), but does **not** declare whether `ignore_permissions` is supported by an Action Type.
2. **Audit Reason Storage Ambiguity**: `_extract_ignore_permissions_audit_reason()` attempts to extract the audit reason from both `action.permission_audit_reason` (top-level DocType field) and `action.config.permission_audit_reason` (JSON config property). This dual-path extraction allows inconsistent frontend implementations to pass validation.

---

## 6. Runtime Execution Traces

### 6.1 Trace 1: `Document Action` (Update Existing Record)

```
Rule Engine Dispatcher (engine.py)
  ↓
DocumentActionHandler.execute(action, context, engine)
  ↓
can_ignore_permissions(action, context, throw=True)
  ├── Checks frappe.session.user roles against {"System Manager"}
  └── Validates presence of permission_audit_reason
  ↓
DocumentActionHandler._update_existing(reference_doctype, config, context, action, ignore_permissions)
  ↓
if not ignore_permissions:
    frappe.has_permission(reference_doctype, "write", docname, parent_doc=...) [THROWS IF DENIED]
  ↓
doc.save(ignore_permissions=ignore_permissions)
  ↓
Frappe ORM Document.save()
```

### 6.2 Trace 2: `Query Records` (Query List)

```
Rule Engine Dispatcher (engine.py)
  ↓
QueryRecordsHandler.execute(action, context, engine)
  ↓
can_ignore_permissions(action, context, throw=True)
  ↓
QueryRecordsHandler._query_list(reference_doctype, config, context, action, ignore_permissions)
  ↓
if ignore_permissions:
    frappe.get_all(reference_doctype, filters=..., fields=...)
else:
    frappe.get_list(reference_doctype, filters=..., fields=...)
```

### 6.3 Trace 3: `Notify` (System Notification - Implicit Bypass)

```
Rule Engine Dispatcher (engine.py)
  ↓
NotifyHandler.execute(action, context, engine)
  ↓
Creates Notification Doc: notification = frappe.new_doc("Notification Log")
  ↓
notification.insert(ignore_permissions=True)  <-- Implicitly forced bypass! No role check or audit reason!
```

---

## 7. Frappe Semantics

| Frappe API Operation                            | Effect of `ignore_permissions=False`                                                    | Effect of `ignore_permissions=True`                                                                  | FlexiRule Engine Usage & Caveats                                                                                        |
| :---------------------------------------------- | :-------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------- |
| `frappe.get_doc(doctype, name)`                 | Validates read permission via `doc.check_permission("read")`.                           | Bypasses read permission check; fetches document regardless of user permissions.                     | Used in `Document Action` and `Query Records` (`_query_doc`).                                                           |
| `frappe.get_list(...)` vs `frappe.get_all(...)` | `get_list` applies User Permissions, Permission Query Conditions, and Role Permissions. | `get_all` bypasses permission query conditions and role permissions, returning all matching records. | `QueryRecordsHandler._query_list` switches between `get_list` (`False`) and `get_all` (`True`).                         |
| `doc.insert()`                                  | Validates `create` permission for DocType and mandatory fields.                         | Bypasses `create` permission check.                                                                  | Used in `Document Action` (`_create_new`). **Note:** Controller `validate()` and `before_insert()` hooks STILL run.     |
| `doc.save()`                                    | Validates `write` permission for DocType and modified fields.                           | Bypasses `write` permission check.                                                                   | Used in `Document Action` (`_update_existing`). **Note:** Controller `validate()` hooks STILL run.                      |
| `frappe.delete_doc(...)`                        | Validates `delete` permission for target DocType.                                       | Bypasses `delete` permission check.                                                                  | Used in `Document Action` (`_delete_record`). Bypasses delete role checks, but linked document constraints still apply. |
| `doc.submit()` / `doc.cancel()`                 | Validates `submit` / `cancel` role permissions and docstatus transitioning.             | Bypasses role permission check for submission/cancellation.                                          | `Document Action` uses `doc.submit()` and `doc.cancel()`.                                                               |

---

## 8. Security Analysis & Execution Contexts

### 8.1 Trust Boundaries & Privilege Escalation Risks

1. **Interactive DocEvents / Web Form Submissions**:
   When a rule is triggered by an interactive user (e.g., a standard employee saving a Purchase Order), `frappe.session.user` is set to that employee's user ID.
   If an administrator configured a `Document Action` in that rule with `ignore_permissions = True` (e.g., to auto-create a GL Entry or update a restricted Stock Ledger entry), `can_ignore_permissions()` will check the **triggering user's** roles (`frappe.session.user`).
   _Privilege Escalation Bug_: Because the non-admin employee lacks the `System Manager` role, `can_ignore_permissions()` throws a `PermissionError` during rule execution, even though the rule was intentionally designed by an administrator to perform a system-level operation!
2. **Background Queue (`rq` tasks) & Scheduled Jobs**:
   When rules execute asynchronously in background queues (`is_async = True`) or via `Rule Scheduler`, `frappe.session.user` defaults to `"Administrator"` or `"Guest"`.
   _Inconsistency_: If `frappe.session.user` is `"Administrator"`, `can_ignore_permissions()` succeeds unconditionally. If `frappe.session.user` falls back to `"Guest"`, it fails. Security behavior is non-deterministic based on execution context.

---

## 9. Discovered Inconsistencies & Bugs

1. **Bug A: Generic Exposure without Backend Handler Consumption**
   _Evidence_: `Rule Action` DocType includes `ignore_permissions` for all nodes, but Action Handlers like `assignment.py`, `condition.py`, `process.py`, `loop.py`, `switch.py` completely ignore it.
2. **Bug B: Query Report `ignore_permissions` Silent No-Op**
   _Evidence_: `flexirule/ruleflow/core/action_handlers/query_records.py` line 1176 explicitly notes: `"Note: ignore_permissions is a no-op for Query Report mode"`. The UI still shows the checkbox when `Query Report` mode is selected.
3. **Bug C: Implicit Unaudited Permission Bypass in Notifications**
   _Evidence_: `flexirule/ruleflow/core/action_handlers/simple_actions.py` line 404 forces `notification.insert(ignore_permissions=True)` without checking `can_ignore_permissions()` or requiring an audit reason.
4. **Bug D: Session User Conflict on Rule Authoring vs. Rule Triggering**
   _Evidence_: `can_ignore_permissions()` checks the role of `frappe.session.user` (the user executing the event) rather than verifying whether the rule was authored/saved by an authorized `System Manager`.
5. **Bug E: Silent Default Injection of Permission Audit Reason in Frontend Stores**
   _Evidence_: `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js` (line 250) and `useGraphStore.js` (line 1872) auto-populate `permission_audit_reason = "System Rule Execution"` if the field is empty upon saving or initializing nodes. This silently satisfies backend audit reason validation without forcing rule authors to provide genuine, meaningful audit justifications for bypassing permission controls.

---

## 10. Correct Behavioral Specification

1. **Explicit Permission Intent**: `ignore_permissions` must only apply to Action Types that directly interact with Frappe's Document ORM or Database Query engine (`Document Action`, `Query Records`, `Sub-Rule`).
2. **Author-Time Permission Elevation**:
    - Permission to _set_ `ignore_permissions = True` must be enforced at **Rule Authoring Time** when the Rule is saved by a `System Manager` or `Rule Builder`.
    - Once validated and saved by an authorized administrator, the rule's execution with `ignore_permissions = True` represents trusted system policy and must execute reliably regardless of which non-admin end-user triggered the event.
3. **Mandatory Audit Logging**:
    - Every rule action executed with `ignore_permissions = True` must record an audit entry containing: `rule_name`, `action_id`, `triggering_user`, `configured_audit_reason`, and `timestamp`.

---

## 11. Recommended Architecture

### Refactoring to Option B / Option D Hybrid Model

```
Rule Action
  ├── action_type (e.g. "Document Action")
  ├── config (JSON / Typed dict)
  │     ├── reference_doctype
  │     ├── operation
  │     └── settings
  │           ├── ignore_permissions (Boolean - Action Type specific)
  │           └── permission_audit_reason (String - Mandatory if ignore_permissions is True)
  └── execution_capabilities (Derived from Action Contract)
```

1. **Remove Top-Level DocType Fields**: Deprecate `ignore_permissions` and `permission_audit_reason` from the generic `Rule Action` child DocType schema.
2. **Contract-Driven Field Exposure**: Define `ignore_permissions` support strictly inside the backend `ActionContract` definition (`flexirule/ruleflow/core/action_handlers/base_contract.py`):

```python
class ActionContract:
    def __init__(self, action_type, supports_ignore_permissions=False, ...):
        self.supports_ignore_permissions = supports_ignore_permissions
```

3. **Dynamic UI Rendering**: Update `ActionSettings.vue` and `ConfigurationPanel.vue` to inspect `contract.supports_ignore_permissions`. If `false`, the UI will not render permission bypass controls.

---

## 12. Action-Type-by-Action-Type Recommendations

| Action Type         | Recommended Architecture Decision      | Reasoning                                                                                         |
| :------------------ | :------------------------------------- | :------------------------------------------------------------------------------------------------ |
| **Document Action** | **Keep & Move to Settings Contract**   | Core ORM write operations (`insert`, `save`, `delete`) need controlled permission bypass.         |
| **Query Records**   | **Keep & Restrict per Mode**           | Enable for `Query List`, `Query Doc`, `Exist Record`. **Remove/Disable** for `Query Report`.      |
| **Sub-Rule**        | **Keep & Retain Flow Context**         | Sub-rule execution context delegation requires propagating elevated permissions.                  |
| **Assignment**      | **Remove Field**                       | Operates on context memory variables and loaded documents; ORM updates happen in Document Action. |
| **Condition**       | **Remove Field**                       | Pure Python/Jinja memory expression evaluation. Bypassing permissions is meaningless.             |
| **Process**         | **Remove Field / Delegate to Process** | Custom Process Python scripts handle their own permission logic.                                  |
| **Notify**          | **Formalize Internal System Context**  | Replace hardcoded `insert(ignore_permissions=True)` with explicit system execution context.       |
| **Raise Error**     | **Remove Field**                       | Terminal exception throwing node. Has no database or permission interactions.                     |
| **Stop**            | **Remove Field**                       | Terminal flow control node.                                                                       |
| **Wait**            | **Remove Field**                       | Flow delay control node.                                                                          |
| **Loop**            | **Remove Field**                       | Iteration flow control node.                                                                      |
| **Switch**          | **Remove Field**                       | Multi-branch routing node.                                                                        |
| **Entry Action**    | **Remove Field**                       | Graph entry point node.                                                                           |

---

## 13. Frontend / Backend Contract Recommendation

### Canonical Contract Schema Specification (`ActionContract`)

```json
{
	"action_type": "Document Action",
	"supports_ignore_permissions": true,
	"required_fields": ["reference_doctype", "operation"],
	"operation_options": ["Create New", "Update Existing", "Delete Record", "Submit", "Cancel"],
	"settings_schema": {
		"ignore_permissions": {
			"type": "Check",
			"label": "Ignore Permissions",
			"default": 0
		},
		"permission_audit_reason": {
			"type": "Small Text",
			"label": "Permission Audit Reason",
			"mandatory_depends_on": "ignore_permissions"
		}
	}
}
```

---

## 14. Test Requirements Specification

To achieve full production readiness, the test suite (`flexirule/ruleflow/tests/`) must be expanded with the following specific test suites:

1. **Role Verification Test Suite (`test_permissions_authoring.py`)**:
    - Verify that a user with the `Rule Builder` role can save a rule containing `ignore_permissions = True`.
    - Verify that a user without `System Manager` or `Rule Builder` cannot save or modify a rule with `ignore_permissions = True`.
2. **Execution Context Test Suite (`test_permissions_execution.py`)**:
    - **Non-Admin Triggering**: Test a non-admin user saving a document that triggers an automated rule containing a `Document Action` with `ignore_permissions = True`. Assert the action executes successfully under rule-author elevation.
    - **Query Records Bypassing**: Test `Query Records` with `ignore_permissions = False` (returns filtered user records) vs `ignore_permissions = True` (returns all records across user permission boundaries).
3. **Contract Compliance Test Suite (`test_action_contracts.py`)**:
    - Iterate through all 13 Action Types and assert that `supports_ignore_permissions` is `False` for non-database nodes (`Condition`, `Assignment`, `Loop`, `Switch`, etc.).

---

## 15. Minimal Implementation Plan (For Future Execution)

1. **Step 1: Schema & Contract Enhancement**
    - Update `ActionContract` class in `base_contract.py` and `contracts.js` to include `supports_ignore_permissions: bool`.
    - Set `supports_ignore_permissions=True` only for `Document Action`, `Query Records`, and `Sub-Rule`.
2. **Step 2: Backend Handler Refactoring**
    - Refactor `can_ignore_permissions()` in `permissions.py` to evaluate rule-author validation during rule save, and execute under authorized context during runtime.
    - Remove silent hardcoded bypasses in `NotifyHandler`.
3. **Step 3: Frontend Dynamic Rendering Refactoring**
    - Update `ActionSettings.vue` to dynamically inspect `supports_ignore_permissions` from the contract.
    - Remove redundant hardcoded `ignore_permissions` controls in `AssignmentConfig.vue`, `LoopConfig.vue`, etc.
4. **Step 4: DocType Field Cleanup & Migration**
    - Deprecate top-level `ignore_permissions` field on `Rule Action` child DocType in favor of structured action settings.
