# FlexiRule Implementation Guide: Developing a New Action Type

This guide provides an exhaustive checklist and gap analysis for adding a new Action Type to FlexiRule.

## Exhaustive Implementation Checklist

### 1. Backend Registration
- [ ] **Define Contract:** Add entry to `ACTION_TYPE_CONTRACT` in `flexirule/ruleflow/core/contracts.py`.
- [ ] **Define Operation (if applicable):** Add entry to `OPERATION_CONTRACTS` in `flexirule/ruleflow/core/contracts.py` for fine-grained field overrides.

### 2. Execution Logic
- [ ] **Create Handler:** New file in `flexirule/ruleflow/core/action_handlers/`.
- [ ] **Register Handler:** Add to `HandlerRegistry._ensure_initialized` in `flexirule/ruleflow/core/action_handlers/__init__.py`.
- [ ] **Implement `execute`:** Handle business logic, resolve values using `ValueResolver`, and return next node ID.

### 3. Frontend Registration
- [ ] **Define Fallback:** Add entry to `DEFAULT_ACTION_TYPE_CONTRACT` in `flexirule/public/js/flexirule/core/contracts.js`.
- [ ] **Add Description:** Add localized description to `ACTION_TYPE_DESCRIPTION` in `contracts.js`.

### 4. Configuration UI
- [ ] **Create Component:** New Vue file in `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/`.
- [ ] **Register Component:** Add to `componentRegistry` and `staticComponentMap` in `flexirule/public/js/flexirule/rule_builder/components/rule_config/ConfigurationPanel.vue`.
- [ ] **Implement Form:** Use standard controls (`ComboBoxControl`, `FlexValueControl`) to edit `node.data.config`.

### 5. Validation & Testing
- [ ] **Backend Validation:** Add type-specific logic to `_validate_action_specifics` in `flexirule/ruleflow/core/validation_service.py` if needed.
- [ ] **Unit Tests:** Add a new test case in `flexirule/ruleflow/tests/test_engine.py` or a dedicated test file.

---

## Gap Analysis & Architecture Recommendations

### Findings
1. **Manual Registration Bottleneck:** Adding an action requires modifying multiple core files (`contracts.py`, `action_handlers/__init__.py`, `contracts.js`, `ConfigurationPanel.vue`).
2. **Hardcoded UI Maps:** The `ConfigurationPanel.vue` uses a static registry which prevents third-party apps from easily adding UI for their own actions.
3. **Contract Redundancy:** Metadata exists in both Python and JS, increasing the risk of desync.

### Recommended Design Improvements
1. **Dynamic Frontend Registration:** Modify `ConfigurationPanel.vue` to use a global component registry that can be extended via `flexirule.bundle.js` or other apps.
2. **Auto-Discovery for Handlers:** Use `pkgutil` or similar to auto-discover and register handlers in the `action_handlers` directory, avoiding manual imports in `__init__.py`.
3. **Enhanced DTO Protocol:** Ensure *all* UI metadata (including descriptions and mapping policies) is sent in the `get_contract_dto` response to reduce reliance on hardcoded JS fallbacks.

---

## Migration & Implementation Strategy

### Phase 1: Preparation (Low Risk)
- Implement Auto-Discovery for backend handlers.
- Refactor `ConfigurationPanel.vue` to support a dynamic registry.

### Phase 2: Feature Implementation (Medium Risk)
- Add the new Action Type following the checklist.
- Verify through automated tests and the Rule Builder UI.

### Phase 3: Cleanup (Low Risk)
- Remove hardcoded descriptions from `contracts.js` once they are successfully served by the DTO.

## Complexity Assessment
- **Small Action (e.g. "Wait"):** ~4-8 hours.
- **Complex Action (e.g. "Query Records"):** ~24-40 hours (requires complex UI and deep execution logic).
- **Architecture Improvement:** ~16-24 hours.

## Risk Matrix
| Risk | Impact | Mitigation |
|------|--------|------------|
| UI/Backend Desync | High | Enforce strict adherence to `get_contract_dto`. |
| Broken Undo/Redo | Medium | Ensure new config components use the reactive store correctly. |
| Performance Loss | Medium | Avoid heavy validation logic in the `execute` loop. |
