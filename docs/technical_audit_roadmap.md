# Technical Audit & Roadmap

This document outlines the current technical state of FlexiRule and provides a roadmap for future improvements.

## Current Technical State

FlexiRule is currently in a **Beta** state, with a stable core engine and a production-ready visual builder.

### Strengths
- **Deterministic Engine**: Graph-based execution with strict cycle detection and visit counting.
- **Unified Contract**: Single source of truth for action metadata shared between Python and Vue 3.
- **High Performance**: Layered caching (Local → Redis → DB) and pre-compiled conditions.
- **Observability**: Detailed execution tracing and persistence for every rule run.
- **Security**: Sandboxed execution and role-based access control (RBAC) at the rule and action level.

### Identified Debt
- **Frontend Bundle Size**: The Vue/VueFlow bundle is large; needs optimization.
- **Condition Complexity**: Very deep nested AND/OR groups in the UI can sometimes produce complex compiled strings.
- **Testing Coverage**: Core engine is well-covered, but edge cases in complex loop/sub-rule interactions need more automated tests.

---

## Technical Roadmap

### **Phase 1: Performance & Scale (Current Focus)**
- [ ] **Partial Registry Updates**: Avoid full registry rebuilds for small rule changes.
- [ ] **Serialized Context Optimization**: Reduce the size of `context_snapshot` in Rule Execution Logs.
- [ ] **Lazy-loading Components**: Optimize the Rule Builder's initialization time.

### **Phase 2: Advanced Orchestration**
- [ ] **Parallel Execution**: Allow nodes to execute in parallel where dependencies allow.
- [ ] **State Machine Integration**: Support long-running rules that pause and wait for external signals (e.g., "Wait for Approval").
- [ ] **Version Diffing**: Visual comparison between rule versions.

### **Phase 3: Ecosystem & Tools**
- [ ] **Visual Debugger**: Step-through debugging directly on the canvas.
- [ ] **Bulk Import/Export**: Better CLI tools for migrating rules between environments.
- [ ] **Rule Analytics**: Dashboard for visualizing performance trends and error hotspots across all rules.

---

## Audit Guidelines for Contributors

When contributing to FlexiRule, ensure that:
1.  **Contracts are Maintained**: Changes to action behavior must be reflected in `contracts.py`.
2.  **Handlers remain Stateless**: Execution context should be passed, never stored in the handler instance.
3.  **Visual Stability**: Graph layout changes should not break existing rules (check `merge_visual_layout`).
4.  **Security First**: Never expose raw `frappe` or `db` methods to rule templates or conditions. Always use `SafeFrappeAPI`.
