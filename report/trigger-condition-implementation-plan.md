# Implementation Plan: Deprecate trigger_condition JSON Field

This plan outlines the steps to migrate the Rule Trigger Condition from the `Rule` DocType to the `Entry Action` config.

## 1. Overview

- **Objective:** Establish `Entry Action` as the single source of truth for trigger logic.
- **Phase 1:** Backend updates & Migration.
- **Phase 2:** Frontend & UI persistence changes.
- **Phase 3:** Cleanup & Field Removal (Future).

---

## 2. Code Changes

### 2.1 Rule DocType (`flexirule/ruleflow/doctype/rule/rule.py`)
- **`compile_conditions()`**:
    - Update to find the `Entry Action` in `self.actions`.
    - Extract JSON from `entry_action.config`.
    - Fallback to `self.trigger_condition` during transition.
    - Compile into `self.compiled_expression`.
- **`validate()`**:
    - Add check to ensure exactly one `Entry Action` exists.
    - Throw error if multiple or zero `Entry Action` nodes are found.

### 2.2 Sub-Rule Handler (`flexirule/ruleflow/core/action_handlers/sub_rule.py`)
- **`execute()`**:
    - Update logic to look for the entry condition JSON inside the resolved sub-rule's `Entry Action` config rather than `rule_doc.trigger_condition`.
    - Maintain fallback to `rule_doc.trigger_condition`.

### 2.3 Rule Coordinator (`flexirule/ruleflow/core/coordinator.py`)
- **`check_eligibility()`**:
    - Update the fallback logic (the "Rule has trigger_condition but no compiled_expression" check) to also check the `Entry Action`.

### 2.4 UI - Rule Builder (`flexirule/public/js/flexirule/rule_builder/...`)
- **`useRuleStore.js`**:
    - In `save_changes()`, stop assigning to `doc.trigger_condition`.
    - Ensure the `Entry Action`'s `config` is correctly serialized with the condition JSON.
- **`useGraphStore.js`**:
    - Update `sync_actions_to_graph` to hydrate the Start Node's `trigger_condition` data from the `Entry Action` config.
- **`StartNodeProperties.vue`**:
    - Update to read/write `trigger_condition` from the node data (which maps to `Entry Action` config). (Note: It already uses `props.nodeData?.trigger_condition`, so the change is mainly in how that data gets into/out of the store).
- **`SubRuleNodeConfig.vue`**:
    - Update compatibility check display logic to read from the sub-rule's Entry Action config instead of `sub_rule.trigger_condition`.
- **`ConditionStep.vue`**:
    - Ensure it correctly handles the mapping when used within a Start Node context.
- **Fixtures & Samples**:
    - Update `flexirule/fixture/rule_sample.json` to move `trigger_condition` data into the Entry Action config.

---

## 3. Migration Strategy

### 3.1 Migration Patch (`flexirule/patches/migrate_trigger_condition_to_entry_action.py`)
- For every `Rule`:
    1. Find or create an `Entry Action` in the `actions` table.
    2. If `Rule.trigger_condition` has data, move it to `Entry Action.config`.
    3. Clear `Rule.trigger_condition` (or keep it if dual-write is preferred during transition).
    4. Re-run `rule.save()` to trigger re-compilation of `compiled_expression`.

### 3.2 Dual-Read Period
- The backend (`rule.py` and `sub_rule.py`) will check **both** locations for a period of one release.
- Priority: `Entry Action.config` > `Rule.trigger_condition`.

---

## 4. Documentation & API Updates

### 4.1 Documentation
- **Developer Guide**: Update Rule Lifecycle documentation to reflect that Trigger Conditions are stored in the Entry Action.
- **API Reference**: Update DocType schema documentation for `Rule` and `Rule Action`.

### 4.2 API Updates
- **`flexirule.ruleflow.api.validate_rule_document`**: Ensure it handles the new location for trigger conditions during pre-save validation.
- **REST API**: Advise users against direct manipulation of `Rule.trigger_condition`.

---

## 5. Validation & Testing

### 5.1 Unit Tests
- Update `flexirule/ruleflow/tests/builder.py` to set conditions on the Entry Action node.
- Add test case for "Missing Entry Action" validation.
- Add test case for "Successful migration" verification.
- Update `flexirule/ruleflow/tests/test_cycles.py`, `test_coordinator.py`, and `test_advanced_rule_flows.py` to use the new Entry Action based configuration.

### 5.2 Integration Tests
- Verify that `Sub-Rule` compatibility checks still work for rules migrated to the new format.

### 5.3 UI Verification
- Open Rule Builder for an existing rule: verify Trigger Condition is loaded correctly.
- Save a rule: verify JSON is stored in the `Rule Action` table and `compiled_expression` is updated.

---

## 6. Rollback Plan

1. **Code:** Revert changes to `Rule.py`, `useRuleStore.js`, etc.
2. **Data:** Run a reverse patch that moves JSON from `Entry Action.config` back to `Rule.trigger_condition` if the latter is empty.
3. **Cache:** Clear the `RuleCoordinator` cache.
