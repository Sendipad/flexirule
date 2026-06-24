# Audit Report 06: Remediation & Patching Plan

## Phase 1: Core Action Fixes
1. **Enable Stop Configuration:**
   - Modify `flexirule/ruleflow/core/contracts.py` to set `Stop` as `configurable: True`.
   - Update `ACTION_TYPE_CONTRACT` to include `config_component: "StopConfig"`.
   - Create/verify the corresponding Vue component.

2. **Restore Switch Action:**
   - Update the `Rule Action` DocType in Frappe to include `Switch` in the `action_type` Select options.
   - Remove `Switch` from `DEFAULT_RELEASE_DISABLED_ACTION_TYPES` in `flexirule/public/js/flexirule/core/contracts.js`.

## Phase 2: Logic & Validation Enhancement
1. **Validation Parity:**
   - Enhance `validation_service.py` to perform a `safe_eval` dry-run on all compiled expressions and Jinja templates during the `Rule.validate` step.

2. **Recursion Expansion:**
   - Increase `MAX_SUB_RULE_DEPTH` to 5 in `engine.py`.

3. **Frontend Label Patch:**
   - Implement `elif` branch handling in `text_generator.js`.

## Phase 3: Documentation & Verification
- Re-run the 50-node stress test.
- Verify that `Stop (Error)` configuration now persists and functions correctly at runtime.
- Verify `Switch` nodes appear in the palette and can be connected.
