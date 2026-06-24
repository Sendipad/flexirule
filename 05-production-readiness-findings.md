# Audit Report 05: Production Readiness Findings

## 1. Critical Bugs (Must Fix)
1. **Stop Action UI Missing:** Users cannot configure the error message for Terminal nodes, making "Stop on Error" logic unusable.
2. **Switch Action Metadata Missing:** `Switch` is missing from the `Rule Action` DocType `action_type` Select options, even though the backend handler is complete.
3. **Activation Parity Gap:** The `validation_service.py` does not dry-run Jinja templates or Python expressions during activation, leading to runtime "surprises" for users.

## 2. Technical Debt
1. **Hardcoded Recursion Limit:** `MAX_SUB_RULE_DEPTH = 2` is too restrictive for enterprise flows.
2. **Assignment Deep Paths:** Lack of child-table support in `AssignmentHandler` forces users to use `Process` (Custom Python) for simple table updates.
3. **Condition Label Logic:** `text_generator.js` is missing `elif` support, leading to misleading graph labels.

## 3. Security Notes
1. **Role Bypass:** The UI does not proactively hide `skip_permissions` for non-admins. It only fails at the save step.
2. **Audit Log Volume:** High-frequency rules (e.g., on `User` login) can generate millions of `Rule Execution Log` entries quickly. No auto-cleanup policy was found in the current codebase.
