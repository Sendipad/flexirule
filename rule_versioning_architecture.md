# Architectural Design: Rule Versioning & Lifecycle Management

## 1. Executive Summary
This document presents the architectural design for Rule Versioning, Safe Editing, and Sub-Rule Lifecycle management within FlexiRule. To ensure stability and safety, FlexiRule will adopt a **Lineage-based Versioning** pattern. This approach decouples parent references from specific versioned documents by using a stable "Base Rule" identity, allowing sub-rules to evolve without breaking active workflows.

---

## 2. Evaluation of Approaches

### Option 1 — Prevent Deactivation
**Description**: Block any attempt to deactivate or modify an active rule if it is referenced by other active parent rules.
*   **Pros**: Zero risk of breaking workflows; simple implementation.
*   **Cons**: Creates "Dependency Lock-in"; poor scalability; frustrating UX.

### Option 2 — Copy-on-Edit / Copy-on-Deactivate
**Description**: Editing an active rule creates a draft copy. The active version remains untouched until the draft is "published".
*   **Pros**: Preserves "Always Active" state; industry-standard workflow.
*   **Cons**: Requires careful management of "which version is active".

### Option 3 — True Rule Versioning (Recommended)
**Description**: Distinguish between the **Logical Identity** (Base Rule) and the **Physical Revision**.
*   **Pros**: Clean references; simple rollbacks; excellent auditability.
*   **Cons**: Requires a resolution layer in the runtime engine.

---

## 3. Recommended Architecture: The Lineage Pattern

Rather than a complete redesign, we will evolve the current model using a **Lineage Identity** strategy.

### Core Concepts
1.  **Base Rule**: The first version of a rule (v1) serves as its permanent logical identity. All subsequent versions (v2, v3, etc.) point back to this document via a `base_rule` field.
2.  **Revision Lineage**: The collection of all documents sharing the same `base_rule`.
3.  **Active Revision**: Exactly one document in a lineage is marked `is_active = 1`. This is the authoritative version used by the runtime.

### Runtime Resolution
The `RuleCoordinator` and `SubRuleHandler` will resolve sub-rules at runtime:
1.  **Logical Reference**: Parent rules point to the `base_rule` of the child.
2.  **Resolution**: The engine fetches the physical name where `base_rule = ref` and `is_active = 1`.
3.  **Caching**: This mapping is stored in the Redis-backed `runtime_registry` for O(1) resolution.

---

## 4. Implementation Roadmap (Incremental Path)

### Phase 1: Lineage Awareness (Low Complexity)
- **Schema**: Add `base_rule` (Link) and `version` (Int) to the `Rule` DocType.
- **Controller**: Enforce "Singleton Active" state—activating a revision automatically deactivates the previous one in the lineage.
- **Amendment**: Enhance `amend_rule` to automatically link the new draft to the original's `base_rule`.

### Phase 2: Logical Sub-Rule Resolution (Medium Complexity)
- **Sub-Rule Action**: Update the `rule` field in `Rule Action` to target the `base_rule`.
- **Runtime**: Update `SubRuleHandler` to resolve the active physical document name from the logical reference.
- **Fallback**: Maintain support for physical links (version pinning) to ensure backward compatibility.

### Phase 3: Dependency & Impact Analysis (Advanced)
- **Recursive Scan**: Build a utility to trace the entire dependency graph (A -> B -> C).
- **Where Used**: Add a UI component to show parents affected by sub-rule changes.
- **Contract Guard**: Compare output schemas between the "Active" and "Draft" revisions to detect breaking changes during publication.

---

## 5. Migration Strategy

1.  **Baseline Patch**: Initialize `base_rule` for all existing rules (pointing vN to v1).
2.  **Pointer Initialization**: Mark the current "Active" document in each lineage as the authoritative version.
3.  **Logical Conversion**: Update `Rule Action` records to point to the `base_rule` instead of specific revisions.
4.  **Zero-Downtime**: The runtime engine remains backward compatible with existing physical links.

---

## 6. Design Fit & Evolutionary Analysis

### Natural Fit
- **Lineage Tracking**: Using Version 1 as the logical identity fits naturally into the existing naming convention (`RuleName_vN`).
- **Amendment Workflow**: The current `amend_rule` function provides a perfect entry point for the "Copy-on-Edit" pattern.
- **Runtime Registry**: The `RuleCoordinator` already manages a global rule map; adding a logical resolution layer is a minor O(1) extension.

### Requires Refactoring
- **Sub-Rule Action Configuration**: The `Rule Action` DocType needs to be updated to distinguish between "Logical" and "Pinned" references.
- **Validation Service**: The `validation_service.py` must be upgraded to support cross-rule dependency tracking and contract comparison.

### Evolutionary Path (The "80-90%" Solution)
Instead of an immediate "Logical Rule" DocType, we can achieve 90% of the benefits by:
1.  Adding a `base_rule` link to the existing `Rule` model.
2.  Enforcing "Single Active" logic in the controller.
3.  Adding a resolution toggle to the Sub-Rule action.

This path avoids a full schema migration while providing the stability and safety requested.

## 7. Risks & Trade-offs
- **Schema Drift**: A sub-rule update that changes output variables may break parents.
  - *Mitigation*: Implement automated contract validation in the "Publish" phase.
- **Complexity**: Explaining "Base Rule" vs "Revision" to users.
  - *Mitigation*: Intuitive UI labels like "Manage Revisions" and "Active Version".
