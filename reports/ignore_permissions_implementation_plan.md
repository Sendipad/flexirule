# Implementation Report: Rename skip_permissions → ignore_permissions (Completed)

## 1. Executive Summary

### Overview & Achievements
This document presents the finalized post-implementation report for renaming the FlexiRule permission bypass concept from its legacy term `skip_permissions` to `ignore_permissions`.

Rather than a simple string-replacement, this change represents a **semantic/domain alignment** with native Frappe Framework terminology, making downstream developer onboarding simpler and reducing cognitive overhead. Within Frappe core:
- Bypassing standard ACL queries on document loading/saving is done via `ignore_permissions=True`.
- Deleting documents with bypass permissions is accomplished via `frappe.delete_doc(..., ignore_permissions=True)`.
- Querying records directly bypassing roles uses `frappe.db.get_all(..., ignore_permissions=True)` or `frappe.get_list(..., ignore_permissions=True)`.

The refactoring has been **fully completed, tested, and verified** across all layers of the system.

### Core Completed Goals
1. **Fully renamed `skip_permissions` to `ignore_permissions`** across all system boundaries (database, backend, API, serialization, hooks, frontend Vue/Pinia stores, tests, and documentation).
2. **Removed stale/dead paths** discovered during the codebase audit (specifically the unread context meta property `sub_context["meta"]["skip_permissions"]` in `sub_rule.py`).
3. **Resolved UI/UX discrepancies** between the legacy Desk Form view (`rule.js`) and the Vue-based Visual Builder, ensuring both interfaces align with the same dynamic contract rules for Query Records and Document Action step types.
4. **Preserved data integrity** for existing production rule setups using a robust database migration strategy (`migrate_skip_permissions.py`).
5. **Established backward compatibility** during the migration window, safely transitioning custom serializations (copy/paste and import/export payloads).
6. **Enforced Report Security**: Documented and verified that top-level Report permissions can never be bypassed, while `ignore_permissions` only applies where explicitly intended (such as Query List/Database operations).

---

## 2. Completed Implementation Analysis

`ignore_permissions` and its dependent `permission_audit_reason` have been successfully implemented across the following layers:

### 2.1 Schema Definition (Database Layer)
- **DocType**: `Rule Action` (a child table of `Rule`)
- **Metadata File**: `flexirule/ruleflow/doctype/rule_action/rule_action.json`
- **Field Definition**:
  - `ignore_permissions` (Type: `Check`, Label: `Ignore Permissions`)
  - `permission_audit_reason` (Type: `Small Text`, Label: `Permission Audit Reason`, mandatory when `ignore_permissions` is true)
- **Auto-generated Class**: `flexirule/ruleflow/doctype/rule_action/rule_action.py` (type annotation: `ignore_permissions: DF.Check`)

### 2.2 Backend Execution & Guards
- **Guard Layer**: `flexirule/ruleflow/core/permissions.py`
  - Function `can_ignore_permissions(action, context=None, throw=True)` checks `getattr(action, "ignore_permissions", getattr(action, "skip_permissions", 0))`, verifies System Manager roles (resolving hooks), and validates the audit reason.
  - Helper `_extract_ignore_permissions_audit_reason(action)` handles extraction from attributes or the JSON configuration field.
- **Action Execution Handlers**:
  - `flexirule/ruleflow/core/action_handlers/document_action.py` uses `can_ignore_permissions()` and propagates `ignore_permissions` to `insert()`, `save()`, `delete_doc()`, and Comment/ToDo overrides.
  - `flexirule/ruleflow/core/action_handlers/query_records.py` uses `can_ignore_permissions()` to derive `ignore_permissions` and bypasses checks in `get_all()`, `get_list()`, etc.
  - `flexirule/ruleflow/core/action_handlers/sub_rule.py` executes nested rules, calling `can_ignore_permissions()` to enforce system-wide security.
- **API Schema generation**: `flexirule/ruleflow/core/graph_service.py` (`get_node_config_schema`) lists `"ignore_permissions"` inside the `"advanced"` fields bucket.

### 2.3 Hooks & Configurations
- **Hooks File**: `flexirule/hooks.py`
- **Dynamic Hook Lookup**: `frappe.get_hooks("flexirule_ignore_permissions_roles")` (falling back to `flexirule_skip_permissions_roles`) is called in `permissions.py` to allow override of default bypass roles (which default to `{"System Manager"}`).

### 2.4 Frontend Representation (Vue & Pinia)
- **Pinia Stores**:
  - `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js` serializes `ignore_permissions: node.data?.ignore_permissions || 0` and auto-populates `permission_audit_reason` default reasons under specific operations.
  - `flexirule/public/js/flexirule/rule_builder/stores/useGraphStore.js` hydrates visual nodes from database attributes, falling back cleanly to `skip_permissions` for backward compatibility.
- **Vue Config Panels**:
  - `QueryRecordsConfig.vue`, `DocumentActionConfig.vue`, and `SubRuleConfig.vue` render form controls mapped to `node.data.ignore_permissions` and `node.data.permission_audit_reason`.
  - Composable `useRuleConfig.js` validates that `permission_audit_reason` is supplied when `ignore_permissions` is enabled.

### 2.5 Legacy Desk UI Alignment
- **Controller File**: `flexirule/ruleflow/doctype/rule/rule.js`
  - In `toggle_action_fields()`, `"ignore_permissions"` and `"permission_audit_reason"` are properly displayed for all relevant action types, resolving the previous UX inconsistency.

---

## 3. Scope of Refactoring (Completed)

This section documents the completed changes across all system components.

### 3.1 Database / DocType Layer

#### `Rule Action` (`rule_action.json`)
The field definition `skip_permissions` has been renamed to `ignore_permissions`.
- **Fieldname change**: `skip_permissions` $\rightarrow$ `ignore_permissions`
- **Depends On**: `permission_audit_reason` depends_on and mandatory_depends_on expressions now use `ignore_permissions`.
  - `"depends_on": "ignore_permissions"`
  - `"mandatory_depends_on": "ignore_permissions"`
- **Auto-generated file update**: Class field annotations in `rule_action.py` have been refreshed:
  ```python
  ignore_permissions: DF.Check
  ```

---

### 3.2 Backend Layer

#### `flexirule/ruleflow/core/permissions.py`
Renamed functions, hooks, variables, and internal exceptions:
- **Renamed function**: `can_skip_permissions` $\rightarrow$ `can_ignore_permissions`
- **Renamed default role constant**: `DEFAULT_SKIP_PERMISSIONS_ROLES` $\rightarrow$ `DEFAULT_IGNORE_PERMISSIONS_ROLES`
- **Renamed custom hook**: `flexirule_skip_permissions_roles` $\rightarrow$ `flexirule_ignore_permissions_roles`
- **Renamed private reason extractor**: `_extract_skip_permissions_audit_reason` $\rightarrow$ `_extract_ignore_permissions_audit_reason`
- **Security log update**: Log warning prefix in `can_ignore_permissions` changed from `"skip_permissions override"` to `"ignore_permissions override"`.

#### `flexirule/ruleflow/core/graph_service.py`
Inside `get_node_config_schema(action_type, operation, process_name)`:
- Renamed the `"skip_permissions"` list element to `"ignore_permissions"` under the `"advanced"` section group:
  ```python
  "fields": ["is_async", "priority", "skip_conditions", "ignore_permissions"]
  ```

---

### 3.3 Action Handlers

Consistently named variables representing permission bypass states within individual handlers are aligned with native Frappe conventions.

#### `flexirule/ruleflow/core/action_handlers/document_action.py`
- Imported helper: `from flexirule.ruleflow.core.permissions import can_ignore_permissions`
- Contract field references inside `get_action_contract()` are mapped to `ignore_permissions`.
- Runtime execution: `ignore_permissions = can_ignore_permissions(action, context, throw=True)`

#### `flexirule/ruleflow/core/action_handlers/query_records.py`
- Imported helper: `from flexirule.ruleflow.core.permissions import can_ignore_permissions`
- Contract field references inside `get_operation_contracts()` are cleanly updated to `ignore_permissions`.
- Runtime execution: `ignore_permissions = can_ignore_permissions(action, context, throw=True)`

#### `flexirule/ruleflow/core/action_handlers/sub_rule.py`
- Imported helper: `from flexirule.ruleflow.core.permissions import can_ignore_permissions`
- Runtime execution: `ignore_permissions = can_ignore_permissions(action, context, throw=True)`
- **Elimination of Dead Context State**: `sub_context["meta"]["skip_permissions"] = skip_permissions` has been successfully eliminated from the execution path to keep context clean.

---

### 3.4 Serialization & Compatibility

To guarantee maximum reliability and prevent breakages when importing, exporting, copying, or pasting legacy rule models:
- **`useGraphStore.js` & `useRuleStore.js`**: Implement safe deserialization/hydration fallback:
  ```javascript
  ignore_permissions: action.ignore_permissions ?? action.skip_permissions ?? 0
  ```
- **`can_ignore_permissions`**: Falls back gracefully to check `getattr(action, "skip_permissions", 0)` if the new database field has not yet been populated or exists on old records.

---

## 4. Database Migration

The database migration is executed smoothly via an idempotent patch pattern.

### Idempotent Migration Patch (`flexirule/patches/migrate_skip_permissions.py`)
This Python patch runs during the upgrade cycle. It reads active values from the old database column and populates the new column.

```python
import frappe

def execute():
	"""Migrate data from deprecated skip_permissions to ignore_permissions."""
	if not frappe.db.has_column("Rule Action", "ignore_permissions"):
		return

	if frappe.db.has_column("Rule Action", "skip_permissions"):
		frappe.db.sql("""
			UPDATE `tabRule Action`
			SET ignore_permissions = skip_permissions
			WHERE skip_permissions = 1
		""")
		frappe.db.commit()
```

The patch is registered in `flexirule/patches.txt` post-model-sync:
```text
flexirule.patches.migrate_skip_permissions
```

---

## 5. Testing & Verification Status

The test suite has been fully updated and verified.

### 5.1 Backend Test Updates

#### File: `flexirule/ruleflow/tests/test_advanced_rule_flows.py`
All inline rule creations using `"skip_permissions": 1` are successfully updated to `"ignore_permissions": 1`.

#### File: `flexirule/ruleflow/tests/test_real_rules.py`
All keyword arguments updated:
- `skip_permissions=1` $\rightarrow$ `ignore_permissions=1`

### 5.2 Verification Commands
All verification checks are passing cleanly:
```bash
# Execute backend tests
bench --site test_site run-tests --app flexirule

# Execute linting and formatting
npm run lint
pre-commit run --all
```
Result: **GREEN / ALL PASSING**
