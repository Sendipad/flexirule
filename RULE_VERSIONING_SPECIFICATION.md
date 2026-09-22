# Architectural Specification: FlexiRule Logical Identity & Versioning

## 1. Data Model Refinement

### Logical Rule vs. Physical Revision
- **Logical ID (`logical_id`)**: A permanent, immutable identifier for a rule (e.g., `CORE_TAX_CALC`). This never changes across versions.
- **Physical Name (`name`)**: The primary key in the database (e.g., `CORE_TAX_CALC_v1`, `CORE_TAX_CALC_v2`).
- **Active Pointer (`is_active_revision`)**: A boolean flag on the `Rule` document. For any given `logical_id`, exactly one document can have `is_active_revision = 1`.

### Updated Schema (Rule DocType)

| Field | Type | Description |
| :--- | :--- | :--- |
| `rule_name` | Data | The human-readable title (e.g., "Tax Calculator"). |
| `logical_id` | Data (Unique) | The system identifier (e.g., `tax_calc_01`). |
| `version` | Int | Revision number (1, 2, 3...). |
| `status` | Select | Draft, Active, Archived, etc. |
| `is_active_revision` | Check | Primary runtime flag. |
| `base_rule` | Link (Rule) | Reference to the first revision (Version 1) of this logical rule. |

---

## 2. Runtime Resolution Logic

### Rule Discovery
The `RuleCoordinator` will maintain a Redis-backed map of `logical_id -> active_name`.

```python
def resolve_active_rule(logical_id: str) -> str:
    """
    Resolves a Logical ID to the current Active physical name.
    """
    # 1. Check Redis Cache
    active_name = cache.get(f"flexirule:active:{logical_id}")
    if active_name:
        return active_name

    # 2. Fallback to DB
    active_name = frappe.db.get_value("Rule",
        {"logical_id": logical_id, "is_active_revision": 1},
        "name"
    )

    # 3. Cache & Return
    if active_name:
        cache.set(f"flexirule:active:{logical_id}", active_name)
    return active_name
```

### Sub-Rule Execution
The `SubRuleHandler` will be updated to:
1. Read the `sub_rule_logical_id` from the action config.
2. Call `resolve_active_rule(logical_id)`.
3. Execute the resolved document.

---

## 3. Dependency & Safety Service

### Recursive Dependency Scan
A new `DependencyService` will provide:
- `get_parents(logical_id)`: Finds all rules that call this logical rule as a sub-rule.
- `get_children(logical_id)`: Finds all sub-rules called by this rule.
- `is_safe_to_deactivate(logical_id)`: Checks if any active parents exist.

### Compatibility Guard
When "Publishing" a new revision, the system performs a **Contract Validation**:
1. Does the new revision maintain the same input requirements?
2. Does the new revision provide the same output schema?
3. If "Breaking Changes" are detected, the user is warned and a "Force Update Parents" or "Side-by-Side" workflow is suggested.

---

## 4. Lifecycle Workflow (UX)

### The "Copy-on-Edit" Pattern
1. **User opens an Active Rule**. The UI is in "Protected Mode" (Read-Only).
2. **User clicks "Create New Draft"**.
   - A new document is created with the same `logical_id` but incremented `version`.
   - `status` = "Draft", `is_active_revision` = 0.
3. **User modifies the Draft**.
4. **User clicks "Publish"**.
   - Validation runs (Recursive).
   - `is_active_revision` on old version is set to 0.
   - `is_active_revision` on new version is set to 1.
   - `RuleCoordinator` cache is cleared.

---

## 5. Implementation Roadmap (Milestones)

### Milestone 1: Core Identity (Weeks 1-2)
- Schema updates to `Rule` DocType.
- Migration patch for existing rules.
- Update `SubRuleHandler` to support logical resolution.

### Milestone 2: Dependency Engine (Weeks 3-4)
- Build the `DependencyService`.
- Implement the "Where Used" UI component.
- Add "Safe Deactivation" checks.

### Milestone 3: Versioning UI (Weeks 5-6)
- Implement "Draft" management in Rule Builder.
- Add "Compare Revisions" view.
- Finalize the "Publish" wizard with impact analysis.
