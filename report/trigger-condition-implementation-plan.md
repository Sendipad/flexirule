# Implementation Plan: Deprecate trigger_condition JSON Field

This document provides a final engineering blueprint for relocating the Rule Trigger Condition from the `Rule` DocType to the `Entry Action` configuration.

## 1. Architectural Principles

- **Action Ownership:** Each action owns its own configuration (Condition Builder JSON).
- **Rule Metadata Boundary:** Rule-level fields contain only metadata or derived runtime artifacts.
- **Runtime Purity:** The engine executes compiled artifacts, not editable configuration.
- **Persistence Decoupling:** UI behavior is independent of persistence details.
- **Encapsulation:** Access to storage format is centralized via APIs.

---

## 2. Core API & Encapsulation

The following methods will be added to the `Rule` class in `flexirule/ruleflow/doctype/rule/rule.py`.

### 2.1 Public Rule API
- **`get_entry_action()`**: Returns the `Rule Action` child document for the rule's entry point.
- **`get_entry_condition()`**: Returns the Condition Builder JSON object. Uses `resolve_entry_condition()` internally.

### 2.2 Compatibility Layer (Internal)
- **`resolve_entry_condition()`**: Implements the dual-read logic (`EntryAction.config` > `Rule.trigger_condition`) for Release N only.

*Note: `set_entry_condition()` is intentionally omitted from the public API as repository analysis shows persistence is handled via standard child-table save flows in the UI store.*

---

## 3. Compilation Pipeline Integration

The existing compilation pipeline in `Rule.compile_conditions()` will be reused. The ONLY modification is the source of the input:

```python
# Before
compiled = compiler.compile(self.trigger_condition)

# After
condition_json = self.get_entry_condition()
compiled = compiler.compile(condition_json)
```

---

## 4. Migration Strategy (Conservative)

### 4.1 Migration Patch
The patch will be strictly idempotent and will NOT trigger standard save hooks.

**Logic Flow:**
1. Fetch all Rules.
2. For each Rule:
   - Identify/Create `Entry Action`.
   - **Case A: Clean Move:** Data exists only in `Rule.trigger_condition`. Move to `EntryAction.config`.
   - **Case B: Ambiguous Data:** Data exists in both and differs. **Log as Error and Skip.**
   - **Case C: Multiple Entry Actions:** **Log as Error and Skip.**
   - **Case D: Malformed JSON:** **Log as Error and Skip.**
3. Update via `frappe.db.set_value` to bypass side effects.
4. Call `self.compile_conditions()` to update `compiled_expression`.

---

## 5. Implementation Roadmap

| Release | Milestones |
| :--- | :--- |
| **Release N** | Implement API & `resolve_entry_condition`. Execute conservative migration. |
| **Release N+1** | UI hides `Rule.trigger_condition`. Backend issues `DeprecationWarning`. |
| **Release N+2** | Remove `Rule.trigger_condition` field and compatibility layer. |

---

## 6. Testing Matrix

| Category | Test Objectives |
| :--- | :--- |
| **Migration** | Idempotency, conservative skip on ambiguity. |
| **Compiler** | Generation of `compiled_expression` from new API. |
| **Validation** | Enforcement of topology (Exactly one Entry Action, Root node). |
| **Runtime** | Transition-period execution (Dual-read). |
| **UI** | Verify Start Node persistence to `Rule Action` child table. |

---

## 7. Future Work (Out of Scope)

- Action-level versioning.
- Schema registry for `Action.config`.
- Multi-start support.

---

## 8. Success Criteria

- [ ] 100% of non-ambiguous rules migrated.
- [ ] No direct reads/writes of `Rule.trigger_condition` outside `resolve_entry_condition`.
- [ ] UI behavior is unchanged; persistence redirected.
- [ ] All automated tests pass.
