# Architecture Audit: Deprecating trigger_condition JSON Field

**Status:** Final
**Date:** 2025-05-24
**Author:** Jules

## 1. Executive Summary

This report evaluates the proposal to deprecate the dedicated `trigger_condition` JSON field on the `Rule` DocType and relocate its contents to the `config` field of the `Entry Action`.

The audit concludes that the current architecture suffers from duplicated state and a violation of the "Action owns its configuration" principle. The proposed changes resolve these issues by establishing the `Entry Action` as the single source of truth for the editable trigger definition, while the `Rule` header retains only the compiled runtime artifact.

**Recommendation:** Proceed with the encapsulated implementation.

---

## 2. Repository Findings & Audit

A final repository audit was performed to identify all direct interactions with `Rule.trigger_condition`.

### 2.1 Direct Reads/Writes
- **Backend:** `rule.py`, `coordinator.py`, `sub_rule.py`, and `compile_service.py` read from the field directly.
- **Frontend:** `useRuleStore.js`, `useGraphStore.js`, `StartNodeProperties.vue`, and `ConditionStep.vue` interact with the field for persistence and display.
- **Tests:** Approximately 10 test files manually set `trigger_condition` for setup.

### 2.2 Impact of Changes
The relocation requires centralizing these reads through a new Rule-level API. By implementing `Rule.get_entry_condition()`, we can swap the persistence layer without breaking the high-level logic in the engine or compiler.

---

## 3. Evaluation of the Proposal

### 3.1 Ownership and Data Integrity
The proposal creates a clear boundary:
- **Editable Source:** Lives in the `actions` child table.
- **Compiled Target:** Lives in the `Rule` header.

This separation prevents the "split brain" scenario where the JSON and the Python expression might belong to different logical steps.

### 3.2 Consistency
By moving the trigger logic into an action, we treat the "Start" of a rule as a first-class action node, making it consistent with "Condition" and "Switch" nodes.

### 3.3 Risks
- **Topology Fragmentation:** If a rule loses its `Entry Action`, it loses its trigger definition. Robust validation in `Rule.validate()` is required to ensure exactly one Entry Action exists.
- **Migration Ambiguity:** Rules with data in both the old and new locations must be handled conservatively to avoid data loss.

---

## 4. Final Verdict: Proceed

The transition to an action-owned trigger condition is a necessary step for the maturity of the FlexiRule architecture. It enables future improvements like action-level versioning and cleaner rule exports. The proposed implementation plan addresses all risks through encapsulation and a conservative migration strategy.
