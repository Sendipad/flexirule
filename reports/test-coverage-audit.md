# Test Coverage Audit — FlexiRule

## 1. Automated Test Suite Execution Results

The automated test suite was executed in the test site environment (`test_site`):
- **Execution Command**: `cd ~/frappe-bench && bench --site test_site run-tests --app flexirule`
- **Results**: **414 ran**, **412 passed**, **2 skipped** (Total: 414 tests in 18.21s).
- **Test Suite Location**: `flexirule/ruleflow/tests/` (34 test modules).

```
Ran 414 tests in 18.206s
OK (skipped=2)
```

---

## 2. Regression Test Suite for Confirmed Findings

A dedicated regression test module `flexirule/ruleflow/tests/test_audit_reproductions.py` was implemented and permanently integrated into the test suite to verify fixes for the key findings:
1. **AST Validation & Sandbox Escape (FR-SEC-001)**: `test_FR_SEC_001_ast_validation_stub_sandbox_escape` verifies `validate_safe_eval` throws `ValidationError` when encountering dunder attribute traversal expressions (`__subclasses__`).
2. **Server-Side Template Injection (FR-SEC-002)**: `test_FR_SEC_002_ssti_in_document_action_rendering` verifies `DocumentActionHandler._render_scalar` does not evaluate raw `frappe` module database calls.
3. **SafeFrappeAPI Parameter Guard (FR-SEC-003)**: `test_FR_SEC_003_safe_frappe_api_format_value_dict_override` verifies `SafeFrappeAPI.format_value` blocks custom dictionary overrides as `df`.
4. **Sub-Rule Recursion Depth Limit Enforcement (FR-ENGINE-002)**: `test_FR_ENGINE_002_sub_rule_recursion_depth_propagated` verifies `SubRuleHandler` enforces `MAX_SUB_RULE_DEPTH = 2` when context depth exceeds the limit.
