# Consolidated Audit Findings — FlexiRule

## Master Findings Summary

| Finding ID | Severity | Area | File / Location | Finding Summary | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FR-SEC-001** | **CRITICAL** | Security | `flexirule/ruleflow/core/permissions.py:186` | AST validation stub in `validate_safe_eval` allows Python sandbox escape via dunder attributes | High |
| **FR-SEC-002** | **CRITICAL** | Security | `flexirule/ruleflow/core/action_handlers/document_action.py:642` | Unsanitized Jinja template rendering (`_render_scalar`) permits Server-Side Template Injection (SSTI) | High |
| **FR-SEC-003** | **HIGH** | Security | `flexirule/ruleflow/core/engine.py:165` | `SafeFrappeAPI.format_value` accepts unvalidated `df` dict, bypassing read-only restrictions | High |
| **FR-SEC-004** | **HIGH** | Security | `flexirule/ruleflow/core/permissions.py:136` | Background worker execution defaults to Administrator session user, bypassing `ignore_permissions` role gate | High |
| **FR-DATA-001** | **HIGH** | Data Integrity | `flexirule/ruleflow/core/engine.py:530` | Savepoint rollback failure swallows database error and leaves partial mutations committed | High |
| **FR-ENGINE-001** | **HIGH** | Rule Engine | `flexirule/ruleflow/core/action_plan_cache.py:53` | Wildcard Redis key pattern deletion fails in Redis clusters, leaving stale action plans active | High |
| **FR-ENGINE-002** | **HIGH** | Rule Engine | `flexirule/ruleflow/core/action_handlers/sub_rule.py:85` | Sub-rule execution does not propagate depth counter, leading to unenforced recursion limits and stack overflow | High |
| **FR-BACK-001** | **MEDIUM** | Backend | `flexirule/ruleflow/core/action_handlers/document_action.py:220` | `input_mapping` expressions are evaluated at runtime without compile-time allowed-root validation | High |
| **FR-FE-001** | **MEDIUM** | Frontend | `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js:145` | VueFlow canvas auto-layout execution causes false "is dirty" state on initial document load | High |
| **FR-FE-002** | **MEDIUM** | Frontend | `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js:320` | Double stringification of `condition_json` during save corrupts raw JSON condition payloads | High |
| **FR-FE-003** | **MEDIUM** | Frontend | `flexirule/public/js/flexirule/rule_builder/stores/useGraphStore.js:412` | Duplicating a node reuses the existing `action_id`, causing collision and graph target errors | High |
| **FR-PROC-001** | **MEDIUM** | Process Framework | `flexirule/ruleflow/core/process_sync.py:78` | Filesystem process sync swallows import and JSON syntax errors during migration | High |
| **FR-DATA-002** | **MEDIUM** | Data Integrity | `flexirule/ruleflow/doctype/rule/rule.py:840` | Active version validation lacks row locking (`FOR UPDATE`), permitting concurrent active versions | High |
| **FR-PERF-001** | **HIGH** | Performance | `flexirule/ruleflow/core/action_handlers/document_action.py:480` | N+1 database query pattern during child table row appends in `DocumentActionHandler` | High |
| **FR-DATA-003** | **LOW** | Data Integrity | `flexirule/ruleflow/doctype/rule_execution_log/rule_execution_log.json` | Missing database index on `execution_id` causes full table scans during log lookups | High |
| **FR-DOC-001** | **INFO** | Documentation | `flexirule/ruleflow/README.md` | Discrepancy between documented sub-rule recursion enforcement and actual runtime behavior | High |

---

## Detailed Finding Entries

### FR-SEC-001: AST Validation Stub in `validate_safe_eval` (CRITICAL)
- **File**: `flexirule/ruleflow/core/permissions.py:186`
- **Function/Class**: `validate_safe_eval(expression)`
- **Technical Analysis**: The function executes `compile(expression, "<string>", "eval")` and returns `True` if no syntax error occurs. It performs no AST tree traversal to block access to dangerous Python attributes (`__subclasses__`, `__class__`, `__bases__`, `__import__`). An attacker with Rule Builder access can craft expressions that execute arbitrary shell commands or access system modules inside `frappe.safe_eval`.
- **Trigger**: Saving a rule with a Python expression referencing `__subclasses__()`.
- **Expected Behavior**: Reject expressions containing restricted AST nodes or dunder attributes with a `ValidationError`.
- **Actual Behavior**: Expression compiles successfully and passes validation.
- **Consequence**: Arbitrary Code Execution (RCE) on the Frappe server.
- **Recommended Fix**: Parse the expression with `ast.parse()` and inspect nodes with an `ast.NodeVisitor` that raises `ValidationError` upon encountering attribute names starting with `__` or function call nodes.

---

### FR-SEC-002: Server-Side Template Injection in Document Actions (CRITICAL)
- **File**: `flexirule/ruleflow/core/action_handlers/document_action.py:642`
- **Function/Class**: `DocumentActionHandler._render_scalar`
- **Technical Analysis**: Template rendering passes user-controlled text directly to `frappe.render_template(value, self._template_context(context))`. The context dictionary includes the global `frappe` module object.
- **Trigger**: Entering Jinja expressions such as `{{ frappe.db.sql("...") }}` in action fields like `comment_text` or `description`.
- **Expected Behavior**: Template strings should be evaluated in a sandboxed Jinja environment without access to the `frappe` module or raw database objects.
- **Actual Behavior**: Frappe evaluates the Jinja template with full module access.
- **Consequence**: SQL injection and arbitrary database read/write access.
- **Recommended Fix**: Pass only safe context variables (`doc`, `vars`) to `render_template` and restrict Jinja globals.

---

### FR-SEC-003: SafeFrappeAPI Format Value Bypass (HIGH)
- **File**: `flexirule/ruleflow/core/engine.py:165`
- **Function/Class**: `SafeFrappeAPI.format_value`
- **Technical Analysis**: `format_value` delegates to `frappe.format_value(value, df, doc, currency)` without verifying whether `df` is a genuine `DocField` metadata object. Passing a custom dictionary as `df` allows invoking dynamic formatter paths via `frappe.get_attr`.
- **Trigger**: Passing `{"fieldtype": "Currency", "options": "os.system"}` as `df`.
- **Expected Behavior**: Only accept valid `DocField` objects fetched from `frappe.get_meta()`.
- **Actual Behavior**: Accepts dict objects and executes dynamic formatters.
- **Consequence**: Execution of arbitrary python methods via API proxy.
- **Recommended Fix**: Ensure `df` is an instance of `frappe.model.meta.DocField` or fetch `df` using `frappe.get_meta(doctype).get_field(fieldname)`.

---

### FR-DATA-001: Savepoint Rollback Failure Swallowing (HIGH)
- **File**: `flexirule/ruleflow/core/engine.py:530`
- **Function/Class**: `RuleEngine._execute_graph`
- **Technical Analysis**: In the `on_error == "Rollback"` handling block:
  ```python
  try:
      frappe.db.rollback(save_point=savepoint_name)
  except Exception:
      self._log("WARNING", _("Savepoint rollback failed, raising error"))
  raise
  ```
  If `frappe.db.rollback(save_point=...)` fails, the exception is caught, logged as a warning, and ignored while re-raising the original exception. Consequently, database modifications made before the savepoint remain in the database transaction.
- **Trigger**: An action error occurring after an implicit commit or when savepoints are disabled.
- **Expected Behavior**: A savepoint failure should force a full transaction rollback (`frappe.db.rollback()`).
- **Actual Behavior**: Partial database changes remain committed.
- **Consequence**: Data corruption and inconsistent database state.
- **Recommended Fix**: Fall back to `frappe.db.rollback()` if savepoint rollback raises an exception.

---

### FR-ENGINE-001: Wildcard Redis Pattern Key Deletion Defect (HIGH)
- **File**: `flexirule/ruleflow/core/action_plan_cache.py:53`
- **Function/Class**: `clear_rule_action_plan_cache`
- **Technical Analysis**: The function executes `frappe.cache.delete_keys("flexirule_action_plan_v1:rule_name:*")`. In Frappe v15 with Redis cluster setups, `delete_keys` does not resolve wildcard patterns across cluster shards, leaving old action plans active in Redis.
- **Trigger**: Updating a rule in a multi-worker / cluster environment.
- **Expected Behavior**: All cached action plans for the updated rule are purged immediately.
- **Actual Behavior**: Stale action plans persist in Redis for up to 24 hours.
- **Consequence**: Executing outdated rule logic after saving edits.
- **Recommended Fix**: Track specific version key hashes in a set or use exact key deletion via `frappe.cache.delete_value`.

---

### FR-ENGINE-002: Sub-Rule Recursion Depth Counter Loss (HIGH)
- **File**: `flexirule/ruleflow/core/action_handlers/sub_rule.py:85`
- **Function/Class**: `SubRuleHandler.execute`
- **Technical Analysis**: `SubRuleHandler` initializes a new `RuleEngine` instance for the sub-rule but fails to pass `_sub_rule_depth` inside `execution_context`. Thus `MAX_SUB_RULE_DEPTH = 2` declared in `engine.py` is never enforced during sub-rule execution.
- **Trigger**: Sub-rules calling each other in a loop at runtime.
- **Expected Behavior**: Throw `SubRuleRecursionLimitError` when recursion depth exceeds 2.
- **Actual Behavior**: Causes recursion stack overflow / server crash.
- **Consequence**: Worker process crash / Denial of Service.
- **Recommended Fix**: Pass `_sub_rule_depth = context.get("_sub_rule_depth", 0) + 1` into the child `RuleEngine` context and throw if depth > `MAX_SUB_RULE_DEPTH`.
