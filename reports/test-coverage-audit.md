# Test Coverage Audit — FlexiRule

## 1. Automated Test Suite Execution Results

The automated test suite was executed in the test site environment (`test_site`):
- **Execution Command**: `cd ~/frappe-bench && bench --site test_site run-tests --app flexirule`
- **Results**: **410 passed**, **2 skipped** (Total: 410 tests in 17.37s).
- **Test Suite Location**: `flexirule/ruleflow/tests/` (33 test modules).

```
Ran 410 tests in 17.369s
OK (skipped=2)
```

---

## 2. Test Coverage Analysis & Critical Coverage Gaps

While the test suite achieves a 100% pass rate, deep inspection revealed significant coverage gaps and false confidence scenarios where pass status obscures underlying security and data integrity vulnerabilities:

### 2.1 Missing Security & Sandbox Tests
1. **AST Validation & Sandbox Escape (FR-SEC-001)**: `test_permissions.py` tests role checks but contains zero tests verifying AST validation or attempting sandbox escapes via dunder attributes (`__subclasses__`, `__class__`, `__globals__`).
2. **Server-Side Template Injection (FR-SEC-002)**: `test_comprehensive.py` tests valid Jinja template rendering in `DocumentActionHandler`, but contains no tests passing malicious Jinja or SQL injection payloads through `_render_scalar`.

### 2.2 False Confidence in Mocked Asynchronous Tests
1. **Asynchronous Document Actions (FR-ENGINE-002)**: Tests for `is_async=1` mock `frappe.enqueue` and verify that `{"enqueued": True}` is returned. They do not execute worker jobs end-to-end to verify whether background document insertion failures are recorded in `Rule Execution Log`.
2. **Redis Cache Pattern Deletion (FR-BACK-002)**: Tests in `test_coordinator.py` clear cache using request-local mocks, missing real Redis cluster pattern deletion bugs.

### 2.3 Untested Edge Cases & Fault Injection
1. **Sub-Rule Recursion Depth Limits (FR-ENGINE-001)**: While `test_cycles.py` tests graph cycle detection during rule save, there are zero tests verifying dynamic runtime execution of sub-rules exceeding `MAX_SUB_RULE_DEPTH = 2`.
2. **Savepoint Rollback Failures (FR-DATA-001)**: No tests mock or simulate MariaDB savepoint failure during `on_error="Rollback"` execution to verify transaction state integrity.

---

## 3. Recommended Test Additions

To establish true production readiness, the following regression test modules should be added:
1. `test_security_sandbox.py`: AST validation and dunder import escape prevention.
2. `test_ssti_prevention.py`: Injection payload rejection in `DocumentActionHandler`.
3. `test_async_document_action.py`: End-to-end background worker execution with failed inserts.
4. `test_sub_rule_depth_limit.py`: Runtime `SubRuleRecursionLimitError` verification.
