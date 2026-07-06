# Architecture Audit: Deprecating trigger_condition JSON Field

**Status:** Draft / Final Review
**Date:** 2025-05-24
**Author:** Jules

## 1. Executive Summary

This report evaluates the proposal to deprecate the dedicated `trigger_condition` JSON field on the `Rule` DocType and relocate its contents (the Condition Builder JSON) to the `config` field of the `Entry Action` (Start Node) within the `Rule Action` child table.

The audit confirms that the proposal is architecturally sound, aligns with the decentralized contract model of FlexiRule, and eliminates a duplicated source of truth. By making the `Entry Action` the owner of the entry logic, we achieve a more consistent and maintainable data model.

**Recommendation:** Proceed with the proposed changes.

---

## 2. Current Architecture

Currently, the `Rule` DocType maintains two fields for rule-entry filtering:
1.  **`trigger_condition` (JSON):** The raw configuration from the Condition Builder UI.
2.  **`compiled_expression` (Python):** The optimized Python expression generated from the JSON on save.

### Workflow:
1.  **UI:** The Start Node in the Rule Builder manages `node.data.trigger_condition`.
2.  **Save:** `useRuleStore.js` maps this node data back to `Rule.trigger_condition`.
3.  **Backend:** `Rule.py` calls `ConditionCompiler` to transform `trigger_condition` into `compiled_expression`.
4.  **Runtime:** `RuleCoordinator.py` uses `compiled_expression` for eligibility checks.
5.  **Inter-Rule:** `SubRuleHandler.py` inspects `trigger_condition` to verify compatibility before calling a sub-rule.

### Flaws:
-   **Duplicated State:** Configuration is split between the parent `Rule` and the `Rule Action` child table (where the `Entry Action` lives).
-   **Inconsistency:** Every other logic block in the rule (Conditions, Switches, etc.) stores its configuration within its respective `Rule Action` row. The Entry Condition is the only outlier.

---

## 3. Proposed Architecture

The proposal relocates the source-of-truth JSON from the `Rule` header to the `Entry Action` child record.

### Key Changes:
-   **Source of Truth:** `Entry Action.config`.
-   **Compilation Target:** Remains `Rule.compiled_expression`.
-   **Validation:** Ensuring exactly one `Entry Action` exists per rule is now a critical validation step.

### Evaluation of Storage Options:
Three options were evaluated for the `config` schema:
1. **Root Object (Selected):** The `config` field stores the condition builder object directly (e.g., `{"op": "and", "conditions": [...]}`).
   * *Justification:* Consistent with how the `Condition` action type works. Reduces nesting.
2. **Keyed (e.g., `{"condition": {...}}`):**
   * *Justification:* Allows for future metadata (e.g., "description" or "version" of the condition builder itself) but adds unnecessary boilerplate for the current scope.
3. **Dedicated Field:** Adding a `condition_json` to the child table.
   * *Justification:* Redundant given the existence of the `config` field which is designed for this purpose.

---

## 4. Repository Findings

### 4.1 Backend Usages
-   **`flexirule/ruleflow/doctype/rule/rule.py`**: The `compile_conditions` method currently reads directly from `self.trigger_condition`. It needs to be updated to find the `Entry Action` in `self.actions` and read its `config`.
-   **`flexirule/ruleflow/core/coordinator.py`**:
    -   `_build_runtime_registry` includes `trigger_condition` in the cached metadata. This is used for legacy fallback checks.
    -   `check_eligibility` has a fallback that checks for `trigger_condition` without `compiled_expression`.
-   **`flexirule/ruleflow/core/action_handlers/sub_rule.py`**: Inspects `sub_rule_doc.trigger_condition` to perform compatibility checks when a caller rule doesn't skip conditions.
-   **`flexirule/ruleflow/tests/`**: Multiple tests (`test_coordinator.py`, `test_cycles.py`, `builder.py`) manually set `trigger_condition` on the Rule object.

### 4.2 Frontend Usages
-   **`useRuleStore.js`**: Explicitly maps `startNode?.data?.trigger_condition` to `doc.trigger_condition` during the save cycle.
-   **`useGraphStore.js`**: Hydrates `trigger_condition` into the start node data during rule loading.
-   **`StartNodeProperties.vue`**: Uses the field to determine if the "Open Condition Builder" button should show a success state.

### 4.3 Data Usages
-   **Fixtures/Samples**: `flexirule/fixture/rule_sample.json` contains a `trigger_condition` field.

---

## 5. Evaluation

### Pros:
-   **Single Source of Truth:** All action configuration now lives inside the `actions` table.
-   **Architectural Alignment:** The `Entry Action` already represents the "Start" of the rule; it is logical that it owns the entry criteria.
-   **Cleaner Header:** Reduces clutter on the `Rule` DocType header.
-   **Maintainability:** Easier to implement version diffing or auditing when all logic is in the same child table.

### Cons/Risks:
-   **Migration Complexity:** Must ensure every existing rule (including draft/inactive ones) receives an `Entry Action` if it doesn't have one, and data is moved correctly.
-   **Runtime Lookup:** The `SubRuleHandler` will now need to iterate over `actions` (or use a cached reference) to find the entry condition for compatibility checks, slightly increasing overhead if not handled carefully (though `compiled_expression` is the primary runtime field).
-   **Testing:** Significant number of tests rely on the old field.

### Hidden Coupling:
The relationship between `Rule.compiled_expression` and the `Entry Action` is implicit. If an `Entry Action` is deleted and recreated, the link must remain robust.

---

## 6. Recommendations

### 6.1 Ownership Location
The **Entry Action** is indeed the correct location. It aligns with the "Action owns its Config" paradigm used throughout FlexiRule.

### 6.2 Implementation Strategy
-   **Storage:** Use the root of the `config` object in the `Rule Action` row for the `Entry Action`.
-   **Compilation:** Update the compiler to always look for the `Entry Action` first.
-   **Deprecation:** Use a staged approach. Keep the field on `Rule` but mark it as `hidden` and `read_only` in the UI, eventually removing it.

### 6.3 Invariant Enforcement
Exactly one `Entry Action` must be enforced in `Rule.validate()` and `flexirule/ruleflow/utils/graph_validator.py`.

---

## 7. Final Verdict: Proceed

The proposal significantly improves the architectural cleanliness of the project with manageable risk. The transition should be handled via a robust migration patch and a dual-read period in the backend to ensure zero downtime or execution failures.
