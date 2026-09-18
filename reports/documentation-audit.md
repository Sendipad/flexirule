# Documentation Audit — FlexiRule

## 1. Scope & Verification Approach

The documentation audit compared user guides, technical documentation under `flexirule/docs/` and `flexirule/ruleflow/README.md`, inline code docstrings, and action contracts against actual runtime implementation in Python and JavaScript.

---

## 2. Documented vs. Implemented Discrepancies

### Discrepancy FR-DOC-001 — Sub-Rule Recursion Depth Limit
- **Documentation**: `flexirule/ruleflow/README.md` and user guides document that sub-rule nesting depth is limited to a maximum depth of 2 levels (`MAX_SUB_RULE_DEPTH = 2`).
- **Implementation**: `flexirule/ruleflow/core/engine.py` declares `MAX_SUB_RULE_DEPTH = 2`, but `SubRuleHandler` in `sub_rule.py` fails to pass depth counters to nested `RuleEngine` instances, leaving recursion depth unenforced at runtime.

---

### Discrepancy FR-DOC-002 — Action Configuration Mode Option Values
- **Documentation**: UI documentation states that action configuration mode options are `"Sidebar"` and `"Dialog"`.
- **Implementation**: `RuleFlow Settings` DocType definition and backend patches define the field literal values as `"Sidebar"` and `"Dialog"`, but `useRuleStore.js` and `ActionFieldProperties.vue` contain deprecated code references checking for `"modal"` instead of `"Dialog"`.

---

### Discrepancy FR-DOC-003 — `ignore_permissions` Role Requirements
- **Documentation**: Documentation states that `ignore_permissions` on rule actions requires the `System Manager` role.
- **Implementation**: `permissions.py:can_ignore_permissions()` reads roles from hooks (`flexirule_ignore_permissions_roles` or `flexirule_skip_permissions_roles`), falling back to `System Manager`. However, frontend action dialogs hide the `ignore_permissions` checkbox using hardcoded JS checks (`eval:!frappe.user.has_role('System Manager')`), ignoring hook overrides configured on the server.

---

### Discrepancy FR-DOC-004 — Dry-Run Execution Log Persistence
- **Documentation**: User guides state that dry-run simulation mode (`simulate_rule`) does not create or persist `Rule Execution Log` database records.
- **Implementation**: `engine.py:_save_execution_log()` checks `self.context.get("dry_run")` to skip enqueueing logs. However, if `dry_run` is invoked via `test_mode` without explicitly setting `dry_run=True`, log records are enqueued and saved to the database.
