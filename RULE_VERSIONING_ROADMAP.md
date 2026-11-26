# Implementation Roadmap & Migration Strategy: Rule Versioning

## 1. Implementation Roadmap

### Phase 1: Model & Schema Evolution
**Rule DocType Updates**:
- Add `logical_id` (Data, Unique).
- Add `revision_number` (Int).
- Add `is_active_revision` (Check, default=0).
- Add `previous_revision` (Link to Rule).

**Sub-Rule Action Updates**:
- Update the "Rule" field in `Rule Action` to optionally store `logical_id` instead of a specific document name.
- Add `use_latest_active` (Check) to control resolution behavior.

### Phase 2: Runtime & Resolution
**RuleCoordinator Updates**:
- Implement `resolve_active_revision(logical_id)` with Redis caching.
- Update `get_applicable_rules` to ensure only the active revision of a DocType Event rule is loaded.

**SubRuleHandler Updates**:
- Modify the `execute` method to resolve the sub-rule at runtime if a logical ID is provided.
- Ensure cycle detection works across logical identities.

### Phase 3: Dependency Discovery & Validation
**Dependency Tracker**:
- Create a utility to build a bi-directional graph of logical rule dependencies.

**Enhanced Validation**:
- Update `validation_service.py` to check for "Breaking Changes" when a new revision is activated (e.g., changed output variable names).

### Phase 4: UI/UX (Rule Builder)
**Draft Management**:
- Implement "Create Draft" button on Active rules.
- Add a "Revision History" sidebar.

**Impact Analysis**:
- Add "View Dependencies" button to show which parent rules will be affected by a change.

**Publish Workflow**:
- Create a modal that summarizes changes and confirms the switch of the "Active" pointer.

---

## 2. Migration Strategy

### Step 1: Data Normalization (Patch)
Create a migration patch (`flexirule/patches/v1_0/initialize_rule_logical_ids.py`):
1. Iterate through all existing Rule documents.
2. If `logical_id` is empty:
   - Generate `logical_id` from the current name (e.g., `VALIDATE_CUSTOMER_v1` -> `VALIDATE_CUSTOMER`).
   - Set `revision_number = 1`.
   - If `is_active == 1`, set `is_active_revision = 1`.

### Step 2: Reference Migration
1. Update existing `Rule Action` records where `action_type == 'Sub-Rule'`.
2. Map the current physical rule link to the corresponding `logical_id`.
3. Set `use_latest_active = 1` by default for existing references.

### Step 3: Runtime Switch
1. Deploy the updated `RuleCoordinator` and `SubRuleHandler`.
2. The engine will now start resolving sub-rules via logical IDs.
3. **Legacy fallback**: If a reference is a physical document name that doesn't match a logical ID, the engine will still load it directly to maintain backward compatibility.

---

## 3. Risk Mitigation

| Risk | Mitigation |
| :--- | :--- |
| **Circular Dependencies** | Dependency service must perform cycle detection during the "Publish" phase, not just at runtime. |
| **Breaking API Changes** | Versioning a sub-rule that removes an output field used by a parent. Validation service must compare output schemas between revisions. |
| **Performance Overhead** | Use Redis caching for logical resolution. The resolution map is small and highly static. |
| **User Confusion** | Provide clear UI indicators (e.g., "YOU ARE EDITING A DRAFT" vs. "VIEWING ACTIVE VERSION"). |
