# Architecture Audit: Deprecating trigger_condition JSON Field

**Status:** Final
**Date:** 2025-05-24
**Author:** Jules

## 1. Executive Summary

This report evaluates the proposal to deprecate the dedicated `trigger_condition` JSON field on the `Rule` DocType and relocate its contents to the `config` field of the `Entry Action`.

The audit concludes that the current architecture suffers from duplicated state and a violation of the "Action owns its configuration" principle. The proposed changes resolve these issues by establishing the `Entry Action` as the single source of truth for the editable trigger definition, while the `Rule` header retains only the compiled runtime artifact.

**Recommendation:** Proceed with the encapsulated implementation.

---

## 2. Architectural Principles

- **Action Ownership:** Each action owns its own configuration (Condition Builder JSON).
- **Rule Metadata Boundary:** Rule-level fields contain only metadata or derived runtime artifacts (compiled Python expressions).
- **Runtime Purity:** The execution engine and coordinator operate on compiled artifacts, not editable UI configuration.
- **Persistence Decoupling:** UI behavior is independent of the underlying persistence layer.
- **Encapsulation:** No component should access the internal storage format of another.

---

## 3. Ownership Contract

- **Entry Action (Rule Action child table):** Owns the **editable definition** (Condition Builder JSON).
- **Rule (Header):** Owns only the **runtime artifact** (`compiled_expression`).

No other component should own or duplicate the trigger configuration.

---

## 4. Repository Audit & Reference Classification

Every reference to `trigger_condition` has been audited and classified for the migration.

| Location | Reference Type | Classification | Migration Action |
| :--- | :--- | :--- | :--- |
| `docs/reference/doctypes.md` | Documentation | **Replace** | Update to reflect storage in Entry Action config. |
| `StartNodeProperties.vue` | UI Display | **Replace** | Access via Entry Action config in node data. |
| `SubRuleNodeConfig.vue` | UI Display | **Replace** | Access via sub-rule's `get_entry_condition()` API. |
| `ConditionStep.vue` | UI Logic | **Replace** | Ensure correct targeting of the `config` field. |
| `useRuleStore.js` | UI Persistence | **Remove/Replace** | Stop writing to Rule field; ensure mapping to child record. |
| `useGraphStore.js` | UI Hydration | **Replace** | Hydrate from Entry Action config via Rule API. |
| `rule.json` / `rule.js` | Meta/UI | **Temporary Compatibility** | Keep field (hidden) for Release N; remove in Release N+2. |
| `rule.py` | Backend Logic | **Temporary Compatibility** | Move to `resolve_entry_condition()` helper. |
| `sub_rule.py` | Backend Logic | **Replace** | Use `sub_rule_doc.get_entry_condition()`. |
| `coordinator.py` | Runtime Registry | **Replace** | Use `rule_doc.get_entry_condition()` during build. |
| `compile_service.py` | Compilation | **Replace** | Use `rule_doc.get_entry_condition()`. |
| `tests/builder.py` | Test Setup | **Replace** | Setup Entry Action config. |
| `tests/*.py` | Test Cases | **Replace** | Update mocks/setups to use new storage. |
| `fixture/rule_sample.json` | Sample Data | **Replace** | Relocate JSON to Entry Action row. |
| `README.md` | Documentation | **Replace** | Update architectural description. |

---

## 5. Evaluation & Verdict

The transition to an action-owned trigger condition is a necessary step for the maturity of the FlexiRule architecture. It enables future improvements like action-level versioning and cleaner rule exports. The proposed implementation plan addresses all risks through encapsulation and a conservative migration strategy.

**Final Verdict: Proceed.**
