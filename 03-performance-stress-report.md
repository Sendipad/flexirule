# Audit Report 03: Stress Test & Performance Profile

## 1. Stress Test Parameters
- **Graph Complexity:** 50 nodes.
- **Node Density:** Mixed (10 Conditions, 10 Assignments, 10 Processes, 10 Document Actions, 10 Notify).
- **Concurrent Rule Execution:** 21 rules on a single `ToDo` save event.

## 2. Findings

### A. Execution Step Limit
The `RuleEngine` terminates execution if more than 1000 steps are taken.
- **Verification:** Created a circular loop (Loop -> Assignment -> Loop). Engine successfully aborted with `CycleDetectedError` after 1000 iterations.

### B. Priority Cap
Rules are dispatched based on the `priority` field (Integer). Frappe's standard priority UI/logic often implies 0-20.
- **Finding:** If more than 21 rules are active for the same event, the priority collisions lead to non-deterministic execution order for rules sharing the same priority index.

### C. Recursion Exhaustion
The sub-rule call depth is hardcoded to `MAX_SUB_RULE_DEPTH = 2`.
- **Verification:** A calls B, B calls C. C calling D triggers `CycleDetectedError`.
- **Risk:** Heavily modularized business logic will hit this wall quickly.

## 3. Parity Gaps
| Scenario | Behavior |
| :--- | :--- |
| **Malformed Jinja** | Passes Activation validation. Crashes at Runtime. |
| **Invalid Python in Conditions** | Passes Activation validation. Crashes at Runtime. |
| **Deep Path Assignment** | Fails at Save/Activation. |
| **Stop (Error) node** | Fails at Save/Activation due to missing `value_template`. |
