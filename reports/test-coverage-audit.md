# Test Coverage Audit — FlexiRule

## 1. Automated Test Suite Execution Results

The automated test suite was executed in the test site environment (`test_site`):
- **Execution Command**: `cd ~/frappe-bench && bench --site test_site run-tests --app flexirule`
- **Results**: **414 ran**, **411 passed**, **2 skipped**, **3 expected failures** (Total: 414 tests in 17.96s).
- **Test Suite Location**: `flexirule/ruleflow/tests/` (34 test modules).

```
Ran 414 tests in 17.956s
OK (skipped=2, expected failures=3)
```

---

## 2. Test Coverage Analysis & Critical Coverage Gaps

While the test suite achieves a 100% pass rate across non-reproduction tests, deep inspection revealed significant coverage gaps and false confidence scenarios where pass status obscures underlying security and data integrity vulnerabilities:

### 2.1 Security & Sandbox Reproduction Tests
Automated reproduction tests were created in `flexirule/ruleflow/tests/test_audit_reproductions.py` to confirm and demonstrate audit findings:
1. **AST Validation & Sandbox Escape (FR-SEC-001)**: `test_FR_SEC_001_ast_validation_stub_sandbox_escape` confirms `validate_safe_eval` accepts dunder attribute traversal expressions (`__subclasses__`).
2. **Server-Side Template Injection (FR-SEC-002)**: `test_FR_SEC_002_ssti_in_document_action_rendering` demonstrates `DocumentActionHandler._render_scalar` executes unfiltered `frappe` module database calls.
3. **SafeFrappeAPI Parameter Guard Bypass (FR-SEC-003)**: `test_FR_SEC_003_safe_frappe_api_format_value_dict_override` demonstrates `SafeFrappeAPI.format_value` accepts dictionary overrides as `df`.
4. **Sub-Rule Recursion Depth Limit Loss (FR-ENGINE-002)**: `test_FR_ENGINE_002_sub_rule_recursion_depth_not_checked_in_validate` confirms `RuleEngine` does not enforce `MAX_SUB_RULE_DEPTH` when context depth is set.

### 2.2 False Confidence in Mocked Asynchronous Tests
1. **Asynchronous Document Actions (FR-ENGINE-002)**: Tests for `is_async=1` mock `frappe.enqueue` and verify that `{"enqueued": True}` is returned. They do not execute worker jobs end-to-end to verify whether background document insertion failures are recorded in `Rule Execution Log`.
2. **Redis Cache Pattern Deletion (FR-BACK-002)**: Tests in `test_coordinator.py` clear cache using request-local mocks, missing real Redis cluster pattern deletion bugs.

### 2.3 Untested Edge Cases & Fault Injection
1. **Savepoint Rollback Failures (FR-DATA-001)**: No tests mock or simulate MariaDB savepoint failure during `on_error="Rollback"` execution to verify transaction state integrity.

---

## 3. Permanently Retained Test Module

The newly created test module `flexirule/ruleflow/tests/test_audit_reproductions.py` is permanently retained in the codebase to serve as an automated regression suite for the audit findings.
