# Architectural Design Report: Rule Versioning & Lifecycle Management

## 1. Executive Summary
This report presents a comprehensive architectural design for Rule Versioning, Safe Editing, and Sub-Rule Lifecycle management within FlexiRule. To ensure stability, safety, and scalability, we recommend transitioning to a **Logical Identity & Immutable Revision** pattern. This architecture decouples parent references from specific versioned documents, allowing sub-rules to evolve without breaking active workflows.

---

## 2. Comparison of Candidate Approaches

| Feature | Option 1: Prevent Deactivation | Option 2: Copy-on-Edit | Option 3: True Versioning (Recommended) |
| :--- | :--- | :--- | :--- |
| **Safety** | High (Rigid) | High | **High (Flexible)** |
| **Maintenance** | Poor (Brittle) | Moderate | **Excellent** |
| **User Experience** | Frustrating | Good | **Professional & Guided** |
| **Auditability** | Limited | Moderate | **Native & Complete** |
| **Scalability** | Low | Moderate | **High** |

### Why Option 3 Wins:
- **Stability**: Active parents always resolve to the "current best" version of a child without manual intervention.
- **Safety**: Changes are made in isolated drafts and validated against the entire dependency tree before activation.
- **Developer Experience**: Clear distinction between the "Rule" (Intent) and the "Revision" (Implementation).

---

## 3. Recommended Architecture: Logical Identity & Versions

### The Core Concept
We introduce a **Logical Rule** identity that persists forever.
- **Logical ID**: A stable key (e.g., `LOAN_ELIGIBILITY_CHECK`).
- **Revision**: An immutable snapshot document (e.g., `LOAN_ELIGIBILITY_CHECK_v4`).
- **Active Pointer**: A singleton flag that marks which revision is the authoritative "Active" version.

### Runtime Resolution Engine
The `RuleCoordinator` and `SubRuleHandler` are updated to resolve logical IDs at execution time.
- **Redis Cache**: A high-performance map of `logical_id -> current_active_name`.
- **Dynamic Loading**: Sub-rules are loaded by resolving the logical reference, ensuring that the latest validated logic is always used.

---

## 4. Implementation Roadmap (Overview)

### Phase 1: Identity & Schema (Short Term)
- Add `logical_id`, `revision_number`, and `is_active_revision` to the `Rule` DocType.
- Implement the `resolve_active_revision` utility.

### Phase 2: Dependency Discovery (Short Term)
- Develop a recursive service to scan for sub-rule dependencies.
- Build the "Where Used" visualizer for the Rule Builder.

### Phase 3: Managed Editing (Medium Term)
- Implement "Protected Mode" for Active rules.
- Automated "Create Draft" workflow upon edit attempt.

### Phase 4: Compatibility Guard (Long Term)
- Automated contract validation: Compare Input/Output schemas between the old and new revisions during the Publish phase.

---

## 5. Schema & Model Changes

### Rule DocType
- `logical_id` (Data, Unique): The persistent key.
- `revision_number` (Int): Sequential counter.
- `is_active_revision` (Check): Pointer for the runtime engine.
- `previous_revision` (Link): Maintains the lineage.

### Rule Action DocType
- Update `rule` field to support `logical_id` references.
- Add `resolution_policy`: "Always Active" (default) or "Pinned" (for advanced pinning).

---

## 6. Runtime & Orchestration Implications

- **Caching**: Resolution is optimized via Redis. A cache clear is triggered only on "Publish".
- **Recursive Integrity**: Dependency analysis identifies downstream impacts (e.g., Versioning C affects B which affects A).
- **Rollback**: Trivial. Switch the `is_active_revision` flag back to a previous revision and clear the cache.
- **Async Workflows**: Background jobs can store the specific revision name they started with to ensure execution consistency even if a new version is published during the run.

---

## 7. Migration Strategy (Overview)
1. **Baseline Patch**: Automatically assign `logical_id` to all existing rules based on their current names.
2. **Pointer Initialization**: Mark the current "Active" document as the `is_active_revision`.
3. **Reference Update**: Convert existing `Rule Action.rule` links from physical names to logical IDs.
4. **Legacy Fallback**: The engine will continue to support direct physical name links if no logical ID is found, ensuring zero downtime.

---

## 8. Risks & Trade-offs

- **Risk: Breaking Changes**: A sub-rule update changes its output keys.
  - *Mitigation*: Strict contract validation during the Publish workflow.
- **Risk: Performance**: Resolution overhead.
  - *Mitigation*: O(1) Redis lookup ensures sub-microsecond resolution time.
- **Risk: UX Complexity**: Users might find the versioning terminology confusing.
  - *Mitigation*: Use intuitive UI labels like "Modify Active Rule" (which creates a draft) and "Publish Changes".

---

## 9. Comparison with Other Rule Engines
FlexiRule's proposed design aligns with industry standards:
- **Camunda**: Uses "Process Definition Keys" (Logical) and "Deployment Versions" (Physical).
- **Salesforce Flow**: Uses "Flow API Name" (Logical) and unique version numbers.
- **AWS Step Functions**: Uses "State Machine ARN" (Logical) and "Version/Alias" (Physical).

By adopting this pattern, FlexiRule gains the maturity and reliability expected from enterprise-grade orchestration engines.
