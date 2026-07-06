# Implementation Plan: Deprecate trigger_condition JSON Field

This document provides a final engineering blueprint for relocating the Rule Trigger Condition from the `Rule` DocType to the `Entry Action` configuration.

## 1. Architectural Principles

- **Action Ownership:** Each action owns its own configuration (Condition Builder JSON).
- **Rule Metadata Boundary:** Rule-level fields contain only metadata (Rule Name, Priority) or derived runtime artifacts (compiled Python expressions).
- **Runtime Purity:** The execution engine and coordinator operate on compiled artifacts, not editable UI configuration.
- **Persistence Decoupling:** UI behavior is independent of the underlying persistence layer.
- **Encapsulation:** No component should access the internal storage format of another.

---

## 2. Core API & Encapsulation

The following methods will be implemented on the `Rule` class to encapsulate access to the entry condition. All other components (Compiler, SubRuleHandler, etc.) MUST use these methods.

### 2.1 State Management
- **`get_entry_action()`**: Returns the `Rule Action` child document associated with the rule's entry point.
- **`get_entry_condition()`**: Returns the Condition Builder JSON object from the Entry Action.
- **`set_entry_condition(payload)`**: Persists the Condition Builder JSON to the Entry Action.

### 2.2 Compatibility Layer (Release N only)
- **`resolve_entry_condition()`**: Centralized helper that implements the dual-read logic (`EntryAction.config` > `Rule.trigger_condition`). This is the **only** place where dual-read logic should exist.

---

## 3. Ownership Contract

- **Entry Action:** Owns the **editable definition** (Condition Builder JSON).
- **Rule:** Owns the **runtime artifact** (`compiled_expression`).

No other component is permitted to duplicate or own the trigger configuration.

---

## 4. Migration Strategy (Conservative & Deterministic)

### 4.1 Migration Patch (`flexirule/patches/migrate_trigger_condition_to_entry_action.py`)
The patch will be strictly idempotent and will NOT trigger standard save hooks.

**Logic Flow:**
1. Fetch all Rules.
2. For each Rule:
   - Identify `Entry Action`. If missing, create one.
   - **Case A: Clean Move:** Data exists only in `Rule.trigger_condition`. Move to `EntryAction.config`.
   - **Case B: Ambiguous Data:** Data exists in both locations and differs. **Log as Error and Skip.**
   - **Case C: Corrupted Topology:** Multiple `Entry Action` nodes found. **Log as Error and Skip.**
   - **Case D: Malformed JSON:** Log as Error and Skip.
3. Update via `frappe.db.set_value` to bypass lifecycle hooks and side effects.
4. Call `Rule.compile_trigger_expression()` to update the derived runtime field.

---

## 5. Implementation Roadmap

| Release | Milestones |
| :--- | :--- |
| **Release N** | Implement Rule API. Centralize dual-read in `resolve_entry_condition`. Execute conservative migration. |
| **Release N+1** | UI hides `Rule.trigger_condition`. Backend issues `DeprecationWarning` if old field is accessed. |
| **Release N+2** | Remove `Rule.trigger_condition` field. Remove `resolve_entry_condition` compatibility layer. |

---

## 6. Runtime Compatibility Matrix

| Component | Status | Required Modification |
| :--- | :--- | :--- |
| **RuleCoordinator** | No Change | Reads from `Rule.compiled_expression`. |
| **Runtime Registry** | No Change | Signature remains stable. |
| **Execution Engine** | No Change | Logic remains decoupled. |
| **Compiler** | Changed | Uses `Rule.get_entry_condition()`. |
| **Debugger** | No Change | Visualizes `visual_data`. |
| **SubRule Handler** | Changed | Uses `Rule.get_entry_condition()` for sub-rule compatibility. |
| **Import/Export** | No Change | Child tables are exported. |
| **Rule Cache** | No Change | Rebuilds on `compiled_expression` change. |

---

## 7. Expanded Validation

Invariants enforced in `Rule.validate()` and `graph_validator.py`:

- **Exactly One Entry Action:** Throw if zero or multiple exist.
- **Topology:** Entry Action must be the root (no incoming edges).
- **Immutability:** Entry Action type and `action_id` are locked.
- **Deletability:** Entry Action deletion is blocked at the model level.
- **Schema Compliance:** Entry Action config must be a valid JSON object/list.

---

## 8. Testing Matrix

| Category | Test Objectives |
| :--- | :--- |
| **Migration** | Idempotency, conservative skip on ambiguity, fixture migration. |
| **Compiler** | Generation of `compiled_expression` from the new API. |
| **Validation** | Enforcement of topology, existence, and immutability. |
| **Runtime** | Transition-period execution (Release N dual-read). |
| **Backward Compatibility** | Verify sub-rules created in previous versions still validate. |

---

## 9. Future Work (Out of Scope)

The following improvements are enabled by this refactoring but will be addressed in future tasks:
- **Action Versioning:** Fine-grained versioning of individual action configurations.
- **Schema Evolution:** Implementing a schema registry for `Action.config` fields.
- **Generic Trigger System:** Decoupling triggers from `Entry Action` to support multi-start rules.

---

## 10. Success Criteria

- [ ] 100% of non-ambiguous rules migrated successfully.
- [ ] `Rule.trigger_condition` is no longer the source of truth for the compiler.
- [ ] `SubRuleHandler` utilizes the encapsulated Rule API.
- [ ] No direct reads/writes of `Rule.trigger_condition` remain in the codebase.
- [ ] All regression and migration tests pass.
- [ ] Acceptance checklist finalized.
