# Implementation Plan: Deprecate trigger_condition JSON Field

This document provides a comprehensive engineering blueprint for relocating the Rule Trigger Condition from the `Rule` DocType to the `Entry Action` configuration.

## 1. Overview

- **Objective:** Establish `Entry Action` as the single source of truth for trigger logic.
- **Architectural Shift:** Move from parent-level storage to child-level action configuration.
- **Phase 1 (Release N):** Introduce storage, enable dual-read, execute idempotent migration.
- **Phase 2 (Release N+1):** Ignore old field, issue deprecation warnings.
- **Phase 3 (Release N+2):** Remove field and compatibility layers.

---

## 2. Core Abstractions & API

To avoid duplicated lookup logic, the following methods will be added to the `Rule` class in `flexirule/ruleflow/doctype/rule/rule.py`:

- **`get_entry_action()`**: Returns the `Rule Action` document representing the Entry Action.
- **`get_entry_action_config()`**: Returns the parsed JSON configuration from the Entry Action.

All subsystems (Compiler, Coordinator, SubRuleHandler, UI serialization) MUST use these methods.

---

## 3. Storage Schema Contract

The `Entry Action` configuration will store the Condition Builder JSON at the root of the `config` field.

**Example JSON Schema:**
```json
{
  "op": "and",
  "conditions": [
    {
      "left": {"ref": "doc.status"},
      "op": "==",
      "right": {"value": "Open"}
    }
  ]
}
```

**Justification:** This matches the schema used by the `Condition` action type, ensuring a uniform developer experience and simplifying the implementation of the `ConditionBuilder` component.

---

## 4. Migration Strategy (Idempotent & Safe)

### 4.1 Migration Patch (`flexirule/patches/migrate_trigger_condition_to_entry_action.py`)
The patch will be designed to run multiple times without side effects and WITHOUT calling `rule.save()`.

**Logic Flow:**
1. Fetch all Rules.
2. For each Rule:
   - Identify `Entry Action`. If missing, create one.
   - **Case A: Data in both locations:** If `Rule.trigger_condition` and `EntryAction.config` both have data, `EntryAction.config` takes precedence.
   - **Case B: Only old location:** Move `Rule.trigger_condition` to `EntryAction.config`.
   - **Case C: Multiple Entry Actions:** Merge configuration from the first one and delete duplicates (logging a warning).
   - **Case D: Malformed JSON:** Log as an error and skip the specific rule; do not abort the patch.
3. Update database directly via `frappe.db.set_value` or `frappe.db.sql` for the `Rule Action` config and `Rule.compiled_expression` to avoid triggering notifications or unrelated hooks.
4. Call a dedicated `Rule.compile_trigger_expression()` method that updates only the compiled field.

---

## 5. Serialization & UI Flow

The UI behavior remains unchanged, but the persistence layer is redirected.

### 5.1 Load Flow
1. `useRuleStore.fetch()` calls `frappe.client.get`.
2. `useGraphStore.sync_actions_to_graph` identifies the `Entry Action`.
3. Start Node data is hydrated from `Entry Action.config`.

### 5.2 Save Flow
1. Condition Builder writes to Start Node state.
2. `useRuleStore.save_changes()` serializes Graph.
3. Start Node data is mapped to `Rule Action.config`.
4. Backend `Rule.validate()` calls `Rule.compile_conditions()`.
5. Compiler reads via `Rule.get_entry_action_config()`.
6. Compiled string saved to `Rule.compiled_expression`.

---

## 6. Runtime Compatibility Matrix

| Component | Status | Modification Description |
| :--- | :--- | :--- |
| **RuleCoordinator** | No Change | Still reads from `Rule.compiled_expression`. |
| **Runtime Registry** | No Change | Signature still includes `compiled_expression`. |
| **Execution Engine** | No Change | Logic remains decoupled from persistence. |
| **Compiler** | Changed | Input source redirected to `get_entry_action_config()`. |
| **Debugger** | No Change | Visualizes based on `visual_data`. |
| **Scheduler** | No Change | Triggered by system events. |
| **SubRule Handler** | Changed | Inspects sub-rule `Entry Action` for compatibility. |
| **Import/Export** | No Change | Child tables are exported/imported by default. |
| **REST API** | Changed | Documentation updated to target child table. |
| **Rule Cache** | No Change | Rebuilds on `compiled_expression` change. |

---

## 7. Validation Rules

The following invariants will be enforced in `Rule.validate()` and `graph_validator.py`:

- **Existence:** Exactly one `Entry Action` must exist.
- **Topology:** `Entry Action` must be the root node (no incoming edges).
- **Immutability:** `Entry Action` type cannot be changed.
- **Deletability:** `Entry Action` cannot be deleted via UI or API.
- **Schema:** `Entry Action.config` must be a valid JSON object or list.
- **No Dual State:** After Phase 2, `Rule.validate()` will throw an error if `Rule.trigger_condition` contains data that differs from `Entry Action.config`.

---

## 8. Testing Matrix

### 8.1 Migration Tests
- Verify idempotency by running the patch twice.
- Test handling of malformed/empty JSON.
- Test migration of fixtures and sample rules.

### 8.2 Compiler Tests
- Verify `compiled_expression` matches legacy generation.
- Test compilation with empty conditions.

### 8.3 Validation Tests
- Verify error on missing/multiple Entry Actions.
- Verify block on deleting/changing Entry Action.

### 8.4 Runtime & Backward Compatibility
- Verify rules with data ONLY in the old field still execute during Release N.
- Verify sub-rule compatibility checks pass across different storage formats.

---

## 9. Deprecation Timeline

| Release | Milestones |
| :--- | :--- |
| **Release N** | Introduce `get_entry_action` helpers. Enable dual-read. Run migration patch. |
| **Release N+1** | Mark `Rule.trigger_condition` as Deprecated. Start using Entry Action as exclusive source. UI hides old field. |
| **Release N+2** | Remove `Rule.trigger_condition` field. Remove `get_entry_action` fallbacks. |

---

## 10. Success Criteria & Acceptance Checklist

- [ ] All 100% of existing rules successfully migrated to Entry Action config.
- [ ] `Rule.get_entry_action_config()` returns correct JSON for all test cases.
- [ ] `Rule.compiled_expression` is generated correctly from the new location.
- [ ] `SubRuleHandler` correctly identifies compatibility using the new location.
- [ ] Rule Builder UI shows no visible change in behavior for Start Node.
- [ ] No performance regression in `Rule.validate()` or `RuleCoordinator`.
- [ ] All automated tests in the testing matrix pass.
- [ ] Documentation updated to reflect the new architecture.
