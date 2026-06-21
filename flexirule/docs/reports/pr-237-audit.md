# FlexiRule PR 237 Audit Report

## 1. Executive Summary
PR 237 introduces a centralized node status system (`not-configured`, `configured`, `invalid`) and a unified validation mechanism in the Rule Builder. The implementation provides a significant UX improvement by surfacing configuration state directly on the canvas. However, the current approach introduces a performance bottleneck ($O(N^2)$ reactivity overhead) and duplicates business logic in the frontend that should be metadata-driven.

## 2. Merge Recommendation: **Request Changes**
The PR provides a solid conceptual foundation for a unified status system. However, the identified performance bottlenecks ($O(N^2)$ reactivity) and architectural duplication of business rules are blocking concerns that must be resolved before the PR can be merged into the core builder.

---

## 3. Findings

### Critical
*   **None identified.**

### High
*   **Performance ($O(N^2)$ Reactivity):** `useNodeStatus.js` uses `ruleStore.nodes.find()` to locate its own node by ID. Since every node on the canvas (N) initializes this composable, any change to the nodes array triggers N searches of N elements. In large rules (50+ nodes), this will lead to noticeable lag during configuration.
*   **Business Logic Duplication:** The PR hardcodes specific validation rules for `Condition` and `Loop` in `contracts.js`. This logic is already present in the backend `validation_service.py`. This violates the project's principle of deriving frontend validation from backend contracts/metadata.

### Medium
*   **Action Policy Consistency:** The PR introduces `required_config_keys` in the frontend `contracts.js` but does not add it to the backend `contracts.py`. This causes a drift between frontend "light" validation and backend "full" validation.
*   **Loss of Domain Semantics:** Replacing the "Terminal" label in `StopNode.vue` with a generic "Configured" status reduces the visual clarity of the rule's flow termination points.

### Low
*   **Redundant Normalization:** `normalizeActionType` is called multiple times per validation cycle for the same node.
*   **Tooltip Discovery:** Tooltips are the only way to see error details on the canvas, which may be cumbersome for rules with many invalid nodes.

---

## 4. Architecture Concerns
*   **Validation Delegation:** The `contracts.js` module is beginning to accumulate action-specific logic. As the system grows, this should be delegated to the Action Contract DTO or specific handlers to keep the core builder generic.
*   **Metadata vs. Code:** Validation rules like "iterator is required" should be part of the action's metadata, not hardcoded if-statements in a utility file.

## 5. Validation Concerns
*   **Schema Bypass:** The PR uses `required_config_keys` as a parallel validation path to JSON Schema (`contract_v2`). This risks fragmenting validation logic as actions move toward more robust schema-driven configurations.
*   **Duplication:** Hardcoded frontend checks for `Condition` and `Loop` configurations duplicate logic that should reside in backend metadata/contracts.

## 6. UX Concerns
*   **Status Ambiguity:** While `Not Configured` and `Invalid` are distinct states, the visual differentiation (icons only) may be subtle for some users.
*   **Context Loss:** As noted, the removal of the "Terminal" label on Stop nodes degrades rule readability.

## 7. Performance Concerns
*   **Reactive Scope:** Every node computing its full validation state on every keystroke in the builder is acceptable *only if* the lookup is $O(1)$. The current $O(N)$ lookup per node makes it $O(N^2)$ overall.

---

## 8. Recommended Improvements

### 6.1 Optimize Reactivity ($O(1)$ lookup)
Modify `useNodeStatus` to accept the reactive `data` object directly as a parameter. Since node components already receive `props.data`, passing it to the composable eliminates the search.

```javascript
// Recommended change in useNodeStatus.js
export function useNodeStatus(nodeDataRef) {
    // nodeDataRef should be a computed/ref of node.data
    const status = computed(() => getNodeStatus(nodeDataRef.value));
    // ...
}
```

### 6.2 Metadata-Driven Validation
Move `required_config_keys` to the backend `ACTION_TYPE_CONTRACT` in `contracts.py`. This ensures the frontend stays in sync with the backend automatically.

### 6.3 Hybrid Labels for Stop Nodes
Update `NodeStatusIndicator` to support a label override or slot, allowing `StopNode.vue` to show "Terminal" when valid, preserving its domain meaning.

### 6.4 Formalize "Invalid" State
Ensure the "Invalid" state is used to block Rule Activation. A node that is "Not Configured" should also be a blocking error for activation, but can be a warning for drafts.

---

## 7. Audit Conclusion
PR 237 is a valuable contribution that aligns with the goal of making FlexiRule a professional-grade builder. By addressing the performance and logic duplication issues, it will provide a robust foundation for the node status system.
