# Implementation Plan: Rename skip_permissions → ignore_permissions

## 1. Executive Summary

### Overview & Objectives
This document provides a highly structured engineering implementation plan for renaming the FlexiRule permission bypass concept from its legacy term `skip_permissions` to `ignore_permissions`.

Rather than a simple string-replacement refactoring, this change represents a **semantic/domain alignment** with native Frappe Framework terminology. Within Frappe core:
- Bypassing standard ACL queries on document loading/saving is done via `ignore_permissions=True`.
- Deleting documents with bypass permissions is accomplished via `frappe.delete_doc(..., ignore_permissions=True)`.
- Querying records directly bypassing roles uses `frappe.db.get_all(..., ignore_permissions=True)` or `frappe.get_list(..., ignore_permissions=True)`.

By adopting `ignore_permissions` as the canonical domain term inside FlexiRule, we simplify downstream developer onboarding, reduce cognitive overhead, and align closely with native framework conventions.

### Core Goals
1. **Fully rename `skip_permissions` to `ignore_permissions`** across all system boundaries (database, backend, API, serialization, hooks, frontend Vue/Pinia stores, tests, and documentation).
2. **Remove stale/dead paths** discovered during the codebase audit (specifically the unread context meta property `sub_context["meta"]["skip_permissions"]` in `sub_rule.py`).
3. **Resolve UI/UX discrepancies** between the legacy Desk Form view (`rule.js`) and the Vue-based Visual Builder, ensuring both interfaces align with the same dynamic contract rules for Query Records and Document Action step types.
4. **Preserve data integrity** for existing production rule setups using a robust database migration strategy.
5. **Establish backward compatibility** during the migration window, safely transitioning custom serializations (copy/paste and import/export payloads).

---

## 2. Current State Analysis

Based on repository-wide searches and the initial security audit, `skip_permissions` and its dependent `permission_audit_reason` flow through the following layers:

### 2.1 Schema Definition (Database Layer)
- **DocType**: `Rule Action` (a child table of `Rule`)
- **Metadata File**: `flexirule/ruleflow/doctype/rule_action/rule_action.json`
- **Field Definition**:
  - `skip_permissions` (Type: `Check`, Label: `Ignore Permissions`)
  - `permission_audit_reason` (Type: `Small Text`, Label: `Permission Audit Reason`, mandatory when `skip_permissions` is true)
- **Auto-generated Class**: `flexirule/ruleflow/doctype/rule_action/rule_action.py` (type annotation: `skip_permissions: DF.Check`)

### 2.2 Backend Execution & Guards
- **Guard Layer**: `flexirule/ruleflow/core/permissions.py`
  - Function `can_skip_permissions(action, context=None, throw=True)` checks `getattr(action, "skip_permissions", 0)`, verifies System Manager roles (resolving hooks), and validates the audit reason.
  - Helper `_extract_skip_permissions_audit_reason(action)` handles extraction from attributes or the JSON configuration field.
- **Action Execution Handlers**:
  - `flexirule/ruleflow/core/action_handlers/document_action.py` uses `can_skip_permissions()` and propagates `ignore_permissions` to `insert()`, `save()`, `delete_doc()`, and Comment/ToDo overrides.
  - `flexirule/ruleflow/core/action_handlers/query_records.py` uses `can_skip_permissions()` to derive `ignore_permissions` and bypasses checks in `get_all()`, `get_list()`, etc.
  - `flexirule/ruleflow/core/action_handlers/sub_rule.py` executes nested rules, setting a dead flag `sub_context["meta"]["skip_permissions"]` which is never read downstream.
- **API Schema generation**: `flexirule/ruleflow/core/graph_service.py` (`get_node_config_schema`) lists `"skip_permissions"` inside the `"advanced"` fields bucket.

### 2.3 Hooks & Configurations
- **Hooks File**: `flexirule/hooks.py`
- **Dynamic Hook Lookup**: `frappe.get_hooks("flexirule_skip_permissions_roles")` is called in `permissions.py` to allow override of default bypass roles (which default to `{"System Manager"}`).

### 2.4 Frontend Representation (Vue & Pinia)
- **Pinia Stores**:
  - `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js` serializes `skip_permissions: node.data?.skip_permissions || 0` and auto-populates `permission_audit_reason` default reasons under specific operations.
  - `flexirule/public/js/flexirule/rule_builder/stores/useGraphStore.js` hydrates visual nodes from database attributes and clears whitespace-only reasons.
- **Vue Config Panels**:
  - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue`
  - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/DocumentActionConfig.vue`
  - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/SubRuleConfig.vue`
  These components render form controls mapped to `node.data.skip_permissions` and `node.data.permission_audit_reason`.
  - Composable `useRuleConfig.js` validates that `permission_audit_reason` is supplied when `skip_permissions` is enabled.

### 2.5 Legacy Desk UI
- **Controller File**: `flexirule/ruleflow/doctype/rule/rule.js`
  - In `toggle_action_fields()`, `"skip_permissions"` is only shown if the `action_type` is `"Sub-Rule"`, meaning the legacy form interface erroneously hides the bypass option for `Query Records` and `Document Action` nodes, even though they are supported at the database and execution levels.

---

## 3. Rename Scope

This section covers the exact layers and components that require renaming and cleaning.

### 3.1 Database / DocType Layer

#### Target: `Rule Action` (`rule_action.json`)
The field definition `skip_permissions` must be replaced with `ignore_permissions`.
- **Fieldname change**: `skip_permissions` $\rightarrow$ `ignore_permissions`
- **Depends On**: `permission_audit_reason` depends_on and mandatory_depends_on expressions must use `ignore_permissions` instead of `skip_permissions`.
  - Search: `"depends_on": "skip_permissions"` $\rightarrow$ `"depends_on": "ignore_permissions"`
  - Search: `"mandatory_depends_on": "skip_permissions"` $\rightarrow$ `"mandatory_depends_on": "ignore_permissions"`
- **Auto-generated file update**: Run `bench --site [site] migrate` and `export_python_type_annotations` to update the class field annotations in `rule_action.py`:
  ```python
  # Old Annotation
  skip_permissions: DF.Check
  # New Annotation
  ignore_permissions: DF.Check
  ```

---

### 3.2 Backend Layer

#### Target: `flexirule/ruleflow/core/permissions.py`
Rename functions, hooks, variables, and internal exceptions:
- **Rename function**: `can_skip_permissions` $\rightarrow$ `can_ignore_permissions`
- **Rename default role constant**: `DEFAULT_SKIP_PERMISSIONS_ROLES` $\rightarrow$ `DEFAULT_IGNORE_PERMISSIONS_ROLES`
- **Rename custom hook**: `flexirule_skip_permissions_roles` $\rightarrow$ `flexirule_ignore_permissions_roles`
- **Rename private reason extractor**: `_extract_skip_permissions_audit_reason` $\rightarrow$ `_extract_ignore_permissions_audit_reason`
- **Security log update**: Change log warning prefix in `can_ignore_permissions` from `"skip_permissions override"` to `"ignore_permissions override"`.

#### Target: `flexirule/hooks.py`
- If custom hooks are defined inside `flexirule/hooks.py` (e.g. `flexirule_skip_permissions_roles`), rename them to `flexirule_ignore_permissions_roles`.

#### Target: `flexirule/ruleflow/core/graph_service.py`
Inside `get_node_config_schema(action_type, operation, process_name)`:
- Rename the `"skip_permissions"` list element to `"ignore_permissions"` under the `"advanced"` section group:
  ```python
  # Before
  "fields": ["is_async", "priority", "skip_conditions", "skip_permissions"]
  # After
  "fields": ["is_async", "priority", "skip_conditions", "ignore_permissions"]
  ```

---

### 3.3 Action Handlers

Ensure that variables representing permission bypass states within individual handlers are consistently named. Since standard Frappe methods accept `ignore_permissions`, this aligns perfectly.

#### Target: `flexirule/ruleflow/core/action_handlers/document_action.py`
- Rename helper import:
  `from flexirule.ruleflow.core.permissions import can_skip_permissions` $\rightarrow$ `can_ignore_permissions`
- Rename the contract field reference in `get_action_contract()` metadata:
  ```python
  # Before
  "fieldname": "skip_permissions"
  # After
  "fieldname": "ignore_permissions"
  ```
- Change `mandatory_depends_on` and `hidden` evaluators inside the action contract block:
  - `"mandatory_depends_on": "skip_permissions"` $\rightarrow$ `"ignore_permissions"`
  - `"hidden": "eval:!doc.skip_permissions"` $\rightarrow$ `"eval:!doc.ignore_permissions"`
- Call the updated permission handler helper:
  `ignore_permissions = can_ignore_permissions(action, context, throw=True)`

#### Target: `flexirule/ruleflow/core/action_handlers/query_records.py`
- Rename helper import:
  `from flexirule.ruleflow.core.permissions import can_skip_permissions` $\rightarrow$ `can_ignore_permissions`
- Call the updated permission handler helper:
  `ignore_permissions = can_ignore_permissions(action, context, throw=True)`
- **Cleanup Opportunity (Unified Operation Contract)**:
  Add an explicit operation contract override block inside `QueryRecordsHandler` mapping `ignore_permissions` and `permission_audit_reason` rules to align with the constraints present inside `document_action.py` and `sub_rule.py`.

#### Target: `flexirule/ruleflow/core/action_handlers/sub_rule.py`
- Rename helper import:
  `from flexirule.ruleflow.core.permissions import can_skip_permissions` $\rightarrow$ `can_ignore_permissions`
- Change contract field definition (similar to `document_action.py`):
  - `"fieldname": "skip_permissions"` $\rightarrow$ `"ignore_permissions"`
  - `"mandatory_depends_on": "skip_permissions"` $\rightarrow$ `"ignore_permissions"`
  - `"hidden": "eval:!doc.skip_permissions"` $\rightarrow$ `"eval:!doc.ignore_permissions"`
- Update runtime execution logic:
  - Change local variable `skip_permissions` to `ignore_permissions` inside `execute()`.
  - Log execution: `_("Sub-Rule {0}: skip_conditions={1}, ignore_permissions={2}").format(...)`
  - Warning representation: `_("Sub-Rule {0}: Executing with ignore_permissions=True by user {1}")`
- **Cleanup Opportunity (Removal of Dead Context State)**:
  Remove `sub_context["meta"]["skip_permissions"] = skip_permissions` completely from `sub_rule.py` since downstream actions evaluate bypass permissions at their individual node levels and never read this inherited payload state.

---

### 3.4 Rule Execution Context

- In `flexirule/ruleflow/core/action_handlers/sub_rule.py`, the nested execution context hydration previously did:
  ```python
  sub_context["meta"]["skip_permissions"] = skip_permissions
  ```
- Since this has been audited and proven to be dead state (with no downstream consumer checking `context["meta"]["skip_permissions"]` or similar), this dictionary property assignment will be **safely eliminated** to avoid state pollution and potential security confusion. Bypasses in child sub-rules are governed strictly by the child nodes' individual execution configuration.

---

### 3.5 Frontend Layer

All Pinia stores, Vue components, and schema validators must be cleanly shifted to `ignore_permissions`.

#### Target: Vue Configuration Components
- **Files**:
  - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/QueryRecordsConfig.vue`
  - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/DocumentActionConfig.vue`
  - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/SubRuleConfig.vue`
- **Changes**:
  - Update `fieldname: 'skip_permissions'` $\rightarrow$ `fieldname: 'ignore_permissions'` inside the configuration schema definitions.
  - Bind custom checkbox: `:modelValue="node?.data?.skip_permissions"` $\rightarrow$ `:modelValue="node?.data?.ignore_permissions"`
  - Bind update events: `@update:modelValue="(val) => update_action_key('skip_permissions', val)"` $\rightarrow$ `update_action_key('ignore_permissions', val)`
  - Update conditional visibility blocks for audit reason field rendering: `v-if="!!node?.data?.skip_permissions"` $\rightarrow$ `v-if="!!node?.data?.ignore_permissions"`
  - Update Vue validation blocks at the bottom of the config files:
    ```javascript
    if (props.node?.data?.ignore_permissions && !props.node?.data?.permission_audit_reason) {
        // ...
    }
    ```

#### Target: Pinia State Stores
- **File**: `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js`
  - In save/serialize payload construction (around Line 435):
    - `skip_permissions: node.data?.skip_permissions || 0` $\rightarrow$ `ignore_permissions: node.data?.ignore_permissions || 0`
- **File**: `flexirule/public/js/flexirule/rule_builder/stores/useGraphStore.js`
  - In node hydration and duplication mapping:
    - Update `skip_permissions: action.skip_permissions || 0` $\rightarrow$ `ignore_permissions: action.ignore_permissions || 0`

#### Target: Form Config & Validation Composable
- **File**: `flexirule/public/js/flexirule/rule_builder/composables/useRuleConfig.js`
  - Update conditional validation rule (around Line 90):
    ```javascript
    // Before
    draftNode.value.data?.skip_permissions && !draftNode.value.data?.permission_audit_reason
    // After
    draftNode.value.data?.ignore_permissions && !draftNode.value.data?.permission_audit_reason
    ```

#### Target: Legacy Desk UI View (`rule.js`)
- **File**: `flexirule/ruleflow/doctype/rule/rule.js`
  - In list of toggle action fields:
    - Replace `"skip_permissions"` with `"ignore_permissions"`.
  - **Cleanup/Alignment Resolution**:
    Ensure `"ignore_permissions"` and `"permission_audit_reason"` are properly pushed into `fields_to_show` for `Query Records` and `Document Action` step types to resolve the legacy UI inconsistency (currently they are only shown for the `"Sub-Rule"` step type in Desk).
    ```javascript
    if (["Sub-Rule", "Query Records", "Document Action"].includes(row.action_type)) {
        fields_to_show.push("ignore_permissions", "permission_audit_reason");
    }
    ```

---

### 3.6 Serialization & Copy/Paste Contracts

To prevent breakages when importing, exporting, copying, or pasting rule models that might contain the older format:
- **File**: `flexirule/public/js/flexirule/rule_builder/utils/serialization.js` (or inline inside hydration workflows in `useGraphStore.js`)
- **Compatibility Mapper**: Implement a safe deserialization/hydration hook. When loading graph nodes (on paste or import), check if `node.skip_permissions` exists and copy its value to `node.ignore_permissions` before deleting the old key:
  ```javascript
  if (node.skip_permissions !== undefined) {
      node.ignore_permissions = node.skip_permissions;
      delete node.skip_permissions;
  }
  ```

---

## 4. Database Migration Plan

In the Frappe Framework, renaming fields directly in DocType JSON schemas will cause the database migrate engine (`bench migrate`) to instantiate a clean, empty column for the new name (`ignore_permissions`) while retaining the old column (`skip_permissions`) as an orphaned, unmanaged field. Therefore, a **coordinated migration path** is necessary.

### 4.1 Safe Migration Strategy
We strongly recommend a **Multi-Step Idempotent Database Patch Pattern** over direct raw database table renames. This preserves user configuration integrity and operates smoothly across multiple environments.

#### Step 1: Add the New Field
Commit the `rule_action.json` schema updates with the new `ignore_permissions` field added.

#### Step 2: Idempotent Migration Patch (`flexirule/patches/v2_0/migrate_skip_permissions_to_ignore_permissions.py`)
This Python patch runs during the upgrade cycle. It reads active values from the old database column and populates the new column.

Following standard Frappe best practices, the patch must be registered in the **`flexirule/patches.txt`** registry file under the `[post_model_sync]` section so that it executes automatically during `bench migrate` once the schema has been synchronized.

##### Implementation Blueprint:
```python
import frappe

def execute():
    """Migrate skip_permissions values to ignore_permissions in Rule Action table."""

    # 1. Check if the legacy column still exists in DB
    if not frappe.db.has_column("Rule Action", "skip_permissions"):
        return

    # 2. Run raw SQL or direct bulk update to migrate existing data securely
    # This prevents any schema validate rules or hooks from interrupting the patch.
    frappe.db.sql("""
        UPDATE `tabRule Action`
        SET `ignore_permissions` = `skip_permissions`
        WHERE `ignore_permissions` IS NULL OR `ignore_permissions` = 0
    """)

    frappe.db.commit()
```

##### Patches Registration (`flexirule/patches.txt`):
Add the patch file path to the end of the `[post_model_sync]` section:
```text
[post_model_sync]
...
flexirule.patches.v2_0.migrate_skip_permissions_to_ignore_permissions
```

#### Step 3: Delete the Old Field Schema
Once the patch runs, the old `skip_permissions` field is safely retired from the DocType JSON schema.

---

### 4.2 Rollback Considerations
If an upgrade must be reversed:
1. Re-add `skip_permissions` back to `rule_action.json`.
2. Execute a rollback patch executing raw database sync:
   ```sql
   UPDATE `tabRule Action` SET `skip_permissions` = `ignore_permissions`;
   ```

### 4.3 Verification Steps
1. Verify the schema via MySQL/MariaDB terminal:
   ```sql
   DESCRIBE `tabRule Action`;
   ```
   Ensure `ignore_permissions` exists with type `int(1)` (Check) and contains correct 0/1 values where old configurations had them.

---

## 5. Backward Compatibility Decision

To guarantee maximum reliability for live enterprise installations, we propose a **Controlled Deprecation Window** instead of an immediate hard break.

### Options Evaluated

| Feature/Metric | Option A: Hard Break (Remove completely) | Option B: Temporary Compatibility Layer (RECOMMENDED) |
| :--- | :--- | :--- |
| **Upgrade Safety** | Low (Will break un-migrated JSON files and old rule exports) | **High** (Ensures old JSON schema exports import without data loss) |
| **System Cleanliness**| Excellent (No residual legacy code paths) | Good (Minimal compatibility layer to be cleaned in the next release) |
| **Maintenance Cost** | Zero | Very Low (Handles fallback during serialization hydration only) |

### Definitive Recommendation
We recommend **Option B (Temporary Compatibility Layer during the migration window)** with the following guidelines:
1. **Database Level**: Keep the DB migration patch completely transactional. After running the patch and confirming `bench migrate`, the old database column `skip_permissions` can be dropped in a subsequent release.
2. **JSON Payloads (Clipboard & Import/Export)**: Implement a fallback parser inside `flexirule/ruleflow/core/compile_service.py` (or schema loader) and `serialization.js` on the frontend. If a rule configuration structure is loaded from an old string or clipboard containing `skip_permissions`, it must be mapped instantly to `ignore_permissions`.
3. **Deprecation Timeline**: Deprecate `skip_permissions` completely in Release N. In Release N+1, remove all backward compatibility mapping layers and drop the database column `skip_permissions`.

---

## 6. Testing Plan

All unit and integration tests must be rewritten to match the renamed domain concept.

### 6.1 Backend Test Updates

#### File: `flexirule/ruleflow/tests/test_advanced_rule_flows.py`
Identify all inline rule creations using `"skip_permissions": 1` and update them to `"ignore_permissions": 1`.
- Update line 131, 172, 183, 310, 328, 394:
  `"skip_permissions": 1` $\rightarrow$ `"ignore_permissions": 1`

#### File: `flexirule/ruleflow/tests/test_real_rules.py`
Update all keyword arguments:
- Update line 131, 284, 298, 395, 446, 495, 543, 672, 725:
  `skip_permissions=1` $\rightarrow$ `ignore_permissions=1`

#### New Test Case: `test_ignore_permissions_guard`
Add a dedicated test case inside `flexirule/ruleflow/tests/test_permissions.py` validating that:
1. `can_ignore_permissions` correctly permits bypasses for allowed roles with valid audit reasons.
2. An exception is thrown if the user lacks the required `flexirule_ignore_permissions_roles` or if `permission_audit_reason` is empty.

```python
def test_can_ignore_permissions_validation(self):
    """Test that can_ignore_permissions correctly enforces rules."""
    from flexirule.ruleflow.core.permissions import can_ignore_permissions

    # Mock action with ignore_permissions enabled but missing audit reason
    class MockAction:
        ignore_permissions = 1
        permission_audit_reason = ""
        action_label = "Test Action"
        action_id = "test_action"

    action = MockAction()

    # Assert validation error is thrown when audit reason is empty
    with self.assertRaises(frappe.ValidationError):
        can_ignore_permissions(action, throw=True)
```

---

## 7. Documentation Plan

All documents, guides, and readme references must be aligned with the domain rename.

### 7.1 Required Updates
1. **File**: `flexirule/ruleflow/README.md`
   - Update line 138:
     `- Permission auditing via `skip_permissions` with audit reason` $\rightarrow$ `- Permission auditing via `ignore_permissions` with audit reason`
2. **File**: `reports/skip_permissions_usage.md` (or archive this file)
   - It is recommended to keep `skip_permissions_usage.md` unchanged for historical audit references, but append a prominent note at the top redirecting developers to this new document.
3. **Inline Code Documentation**:
   - Update all Docstrings in `permissions.py`, `document_action.py`, `query_records.py`, and `sub_rule.py` containing references to `skip_permissions`.
4. **Release Notes**:
   - Document the breaking semantic rename of `skip_permissions` to `ignore_permissions` in alignment with Frappe native terminology. Mention custom hook migration rules from `flexirule_skip_permissions_roles` to `flexirule_ignore_permissions_roles`.

---

## 8. Implementation Sequence

To perform this refactoring safely, implement changes in the following sequence:

```
┌──────────────────────────────────────────────────────────┐
│ 1. Metadata Schema Update (Add ignore_permissions field)  │
└────────────────────────────┬─────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 2. Create Idempotent DB Migration Patch                  │
└────────────────────────────┬─────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 3. Backend Refactoring (Update Guard & Action Handlers)   │
└────────────────────────────┬─────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 4. Dead Code Cleanup (Sub-rule dead state elimination)   │
└────────────────────────────┬─────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 5. Frontend Alignment (Vue panels, Pinia, & Desk rule.js)│
└────────────────────────────┬─────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 6. Compatibility & Clipboard Hydration Utilities         │
└────────────────────────────┬─────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 7. Test Suite Updates (Modify backend & integration tests)│
└────────────────────────────┬─────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 8. Documentation & Schema Cleanup (Drop legacy field)     │
└──────────────────────────────────────────────────────────┘
```

---

## 9. Validation Checklist

An engineer executing this plan should run the following verification steps:

### 9.1 Source Search (Cleanliness Checks)
Verify that all legacy occurrences are successfully migrated:
```bash
# Expect 0 matches except in patches/ or legacy compatibility logic
git grep -i "skip_permissions" | grep -v "patch"
```

Verify that the new term is present across the codebase:
```bash
# Expect matches in metadata, backend, frontend, and tests
git grep -i "ignore_permissions"
```

### 9.2 Backend Verifications
Run all backend tests to ensure zero regressions:
```bash
bench --site test_site run-tests --app flexirule
```

### 9.3 Frontend & Cypress UI Tests
Build the updated frontend bundle and run UI verification:
```bash
# Compile bundle
npm run build

# Check code formatting and linting
npm run lint
pre-commit run --all

# Run Cypress UI tests to ensure visual editor saves rules successfully
bench --site test_site run-ui-tests flexirule
```

---

## 10. Risk Assessment

### 10.1 Identified Risks & Mitigations

#### Risk A: Data Loss during Upgrade
- **Description**: Upgrading a live database instance drops the old `skip_permissions` column without migrating state, turning off permission bypass flags on critical system rules.
- **Mitigation**: The idempotent migration patch executes first before removing the field metadata. The upgrade script validates that data copy is complete.

#### Risk B: Inoperable Serialized JSON Rules
- **Description**: Rules stored in files or external configurations fail to import because they use the legacy `skip_permissions` key.
- **Mitigation**: The hydration/deserialization helpers on both the backend and frontend automatically translate `skip_permissions` key inputs to `ignore_permissions` transparently during the deprecation window.

#### Risk C: Broken Hooks for Custom Roles
- **Description**: Enterprise customers overrides `flexirule_skip_permissions_roles` in their custom app `hooks.py`, rendering the bypass inaccessible to their system managers post-upgrade.
- **Mitigation**: Provide fallback lookup in `permissions.py`:
  ```python
  allowed_roles = set(
      frappe.get_hooks("flexirule_ignore_permissions_roles") or
      frappe.get_hooks("flexirule_skip_permissions_roles") or
      []
  )
  ```
  This allows existing custom apps' hook settings to continue working while emitting a standard warning deprecation message to logs.
