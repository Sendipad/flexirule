# Backend Audit — FlexiRule

## 1. Overview & Audit Scope

The backend audit focused on all Python modules under `flexirule/ruleflow/`:
- **Core Engine & Orchestration**: `engine.py`, `coordinator.py`, `rule_service.py`, `action_plan_cache.py`, `compiler.py`, `evaluator.py`, `runtime_eval.py`.
- **Action Handlers**: `flexirule/ruleflow/core/action_handlers/` (`document_action.py`, `assignment.py`, `query_records.py`, `simple_actions.py`, `sub_rule.py`, `switch.py`, `loop.py`, `process.py`).
- **Resolvers & Utilities**: `value_resolver.py`, `field_resolver.py`, `mapping.py`, `normalization.py`.
- **Validation & Permissions**: `validation_service.py`, `permissions.py`, `graph_validator.py`.

---

## 2. Detailed Findings

### Finding FR-BACK-001 (HIGH) — Savepoint Rollback Failure Swallowing in Engine Traversal
- **File**: `flexirule/ruleflow/core/engine.py`
- **Function/Class**: `RuleEngine._execute_graph`
- **Description**: In the action traversal loop, when an action fails with `on_error == "Rollback"`, the engine attempts to rollback to a savepoint:
  ```python
  elif current.on_error == "Rollback":
      savepoint_name = f"flexirule_action_{current.action_id or current.name}"
      try:
          frappe.db.rollback(save_point=savepoint_name)
      except Exception:
          self._log("WARNING", _("Savepoint rollback failed, raising error"))
      raise
  ```
- **Technical Analysis**: If `frappe.db.rollback(save_point=...)` fails (for example, if a prior implicit commit released the savepoint or MariaDB savepoint limit was reached), the exception during rollback is swallowed and logged as a warning. The original action exception is then re-raised. As a result, database mutations performed prior to the error remain un-rolled-back in the active transaction, corrupting data integrity.
- **Impact**: Unintended partial database writes committed to the database despite `on_error="Rollback"` policy.
- **Remediation**:
  ```python
  except Exception as rollback_err:
      self._log("ERROR", f"Savepoint rollback failed critically: {rollback_err}")
      frappe.db.rollback() # Fallback to full transaction rollback
      raise
  ```

---

### Finding FR-BACK-002 (HIGH) — Stale Redis Key Pattern Invalidation in Action Plan Cache
- **File**: `flexirule/ruleflow/core/action_plan_cache.py`
- **Function/Class**: `clear_rule_action_plan_cache`
- **Description**: Invalidation attempts to delete Redis keys matching a pattern:
  ```python
  pattern = f"{CACHE_KEY_PREFIX}:{rule_name}:*"
  frappe.cache.delete_keys(pattern)
  if hasattr(frappe.cache, "make_key"):
      frappe.cache.delete_keys(frappe.cache.make_key(pattern))
  ```
- **Technical Analysis**: In Frappe v15 with Redis cluster setups or key prefixing, `frappe.cache.delete_keys` takes raw keys without cluster prefixing or fails silently when wildcard patterns are passed. As a result, old action plans remain cached in Redis for up to 24 hours (`expires_in_sec=86400`), leading to workers executing stale rule logic after a rule has been updated.
- **Impact**: Stale rule execution in multi-worker production environments.
- **Remediation**: Track specific version hashes in a Redis set or use Frappe's `frappe.cache.delete_value` with exact keys derived from active rule versions.

---

### Finding FR-BACK-003 (MEDIUM) — Unsanitized Expression Evaluation in Document Action Input Mappings
- **File**: `flexirule/ruleflow/core/action_handlers/document_action.py`
- **Function/Class**: `DocumentActionHandler.execute`
- **Description**: `apply_input_mapping` processes expressions in input mappings without prior validation against allowed context roots.
- **Technical Analysis**: If an invalid or malicious input mapping string is stored in an action's JSON config (e.g. `{"input_mapping": {"field": "doc.non_existent_field.bad_method()"}}`), the evaluation fails at runtime deep inside action execution rather than during rule save/compile time.
- **Impact**: Uncaught runtime exceptions during rule execution causing rule failure.
- **Remediation**: Call `Rule._validate_allowed_roots()` during `DocumentActionHandler.validate()` and during compile phase in `compile_action_mappings()`.

---

### Finding FR-BACK-004 (LOW) — Unused Legacy Method Dispatch in HandlerRegistry
- **File**: `flexirule/ruleflow/core/action_handlers/__init__.py`
- **Function/Class**: `HandlerRegistry`
- **Description**: Legacy fallback code exists that attempts to dispatch execution to `engine._execute_<type>` methods if a registered handler is missing.
- **Technical Analysis**: All action types are now fully covered by `ActionHandler` subclasses. Leaving legacy fallback code creates technical debt and obscures missing handler bugs during future extensions.
- **Impact**: Maintainability concern.
- **Remediation**: Remove legacy fallback branches and throw explicit `UnregisteredActionHandlerError`.

---

### Finding FR-BACK-005 (LOW) — Inconsistent Keyword Parameter Handling in `SafeFrappeAPI.get_all`
- **File**: `flexirule/ruleflow/core/engine.py`
- **Function/Class**: `SafeFrappeAPI.get_all`
- **Description**: `SafeFrappeAPI.get_all` overrides `limit_page_length` if `limit` is present in `kwargs`:
  ```python
  if "limit" in kwargs:
      limit_page_length = kwargs.pop("limit")
  ```
- **Technical Analysis**: If a rule author passes both `limit=10` and `limit_page_length=50`, `limit` overrides `limit_page_length` without warning, leading to unexpected query page lengths.
- **Impact**: Minor unexpected query behavior.
- **Remediation**: Raise `ValueError` or standardize on `limit_page_length`.
