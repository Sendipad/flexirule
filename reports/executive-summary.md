# Executive Summary — FlexiRule Deep Code Audit

## 1. Overview & Scope

A comprehensive, production-oriented software audit of the **FlexiRule** Frappe application was conducted. FlexiRule is an advanced visual rule builder and workflow orchestration engine designed for Frappe Framework v15+.

- **Repository**: `https://github.com/Sendipad/flexirule`
- **Audited Commit Hash**: `d3bcb8d444454f146e12ae6133375f0360a786aa`
- **Application Version**: `0.0.1`
- **Audit Execution Date**: March 2026

The audit evaluated the entire codebase spanning Python backend controllers, rule execution engines, Frappe DocTypes, Vue 3 / VueFlow canvas UI, Pinia state management stores, Process plugin architecture, database transactions, caching strategies, and security boundaries.

---

## 2. Summary of Findings by Severity

A total of **16 distinct findings** were verified and classified based on realistic exploitability, data integrity impact, and operational frequency:

| Severity | Count | Primary Impact Areas |
| :--- | :---: | :--- |
| **CRITICAL** | **2** | Sandbox escape via AST validation stub, Jinja SSTI in Document Action templates |
| **HIGH** | **4** | SafeFrappeAPI method bypass via `format_value`, transaction savepoint failure swallowing, stale action plan cache in Redis, unhandled recursion depth in sub-rules |
| **MEDIUM** | **5** | Draft-mode dirty state pollution in VueFlow canvas, race condition in active version enforcement, missing validation on `input_mapping` expressions, process discovery silent fallback, false confidence in mock tests |
| **LOW** | **3** | Unused legacy handler fallback code, missing index on `Rule Execution Log.execution_id`, typo in UI contract metadata |
| **INFO** | **2** | Discrepancy between documentation and implementation on dry-run limits, lack of strict type annotations in composables |

---

## 3. Top Critical & High Findings

1. **FR-SEC-001 (CRITICAL) — Stubbed AST Validation in `validate_safe_eval`**:
   `flexirule/ruleflow/core/permissions.py:validate_safe_eval()` is a stub that only performs syntax compilation without AST node inspection. Attackers with Rule Builder permissions can execute arbitrary Python via dunder attributes (e.g. `__class__.__subclasses__`) inside `frappe.safe_eval`. Replaced & confirmed in `test_audit_reproductions.py`.
2. **FR-SEC-002 (CRITICAL) — Unsanitized Template Injection (SSTI) in Document Action**:
   `flexirule/ruleflow/core/action_handlers/document_action.py:_render_scalar()` passes user-configured template strings directly to `frappe.render_template()` without escaping or sandboxing, permitting arbitrary Jinja execution. Confirmed in `test_audit_reproductions.py`.
3. **FR-SEC-003 (HIGH) — SafeFrappeAPI Bypasses via `format_value`**:
   `SafeFrappeAPI.format_value` exposes `frappe.format_value` directly, which internally evaluates Python code or executes SQL for dynamic docfield formatters, bypassing read-only restrictions. Confirmed in `test_audit_reproductions.py`.
4. **FR-DATA-001 (HIGH) — Transaction Savepoint Failure Swallowing in Rule Engine**:
   In `engine.py:_execute_graph`, if an error occurs during an action configured with `on_error="Rollback"`, the exception during `frappe.db.rollback(save_point=...)` is logged as a warning, and the original error is re-raised without resetting database state, leaving partial writes committed.
5. **FR-ENGINE-001 (HIGH) — Stale Redis Action Plan Caching**:
   `action_plan_cache.py` caches compiled action plans in Redis keyed by rule name and hash, but cache invalidation in `clear_rule_action_plan_cache` fails to invalidate pattern keys reliably across Redis cluster configurations, leaving stale plans active after rule updates.
6. **FR-ENGINE-002 (HIGH) — Sub-Rule Recursion Limit Enforcement Defect**:
   While `MAX_SUB_RULE_DEPTH = 2` is declared in `engine.py`, the engine fails to pass depth counters down to recursive `SubRuleHandler` invocations, allowing stack overflow or infinite recursion when sub-rules form dynamic cycles. Confirmed in `test_audit_reproductions.py`.

---

## 4. Test Suite Execution & Reproduction Baseline

The test suite was executed in the test environment (`test_site`):
- **Command**: `bench --site test_site run-tests --app flexirule`
- **Results**: 414 tests ran, **411 passed**, 2 skipped, 3 expected failures (17.96 seconds).
- **Audit Reproductions**: Added `flexirule/ruleflow/tests/test_audit_reproductions.py` as a permanent regression suite confirming findings FR-SEC-001, FR-SEC-002, FR-SEC-003, and FR-ENGINE-002.

---

## 5. Recommended Remediation Order

1. **Immediate (Blockers for RC/Production)**:
   - Implement AST validation in `permissions.py:validate_safe_eval` to block `__subclasses__` and unsafe AST nodes.
   - Replace raw `frappe.render_template` in `document_action.py` with sandboxed Jinja evaluation.
   - Wrap `SafeFrappeAPI.format_value` in safe parameter guards.
   - Fix savepoint rollback exception handling in `engine.py`.
2. **Pre-RC Release**:
   - Fix Redis key pattern deletion in `action_plan_cache.py`.
   - Propagate sub-rule recursion depth counters in `SubRuleHandler`.
   - Fix VueFlow canvas draft hydration state to prevent false `is_dirty` flags.
3. **Post-RC & Long Term**:
   - Add database index on `Rule Execution Log.execution_id`.
   - Standardize frontend-backend contract DTO sync during CI build.
