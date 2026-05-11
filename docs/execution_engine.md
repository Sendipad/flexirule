# Execution Engine Deep Dive

## Execution Pipeline
1. **Trigger** — `doc_events` hook → `RuleCoordinator.execute_rules(doc, event_name)`
2. **Filtering** — Skip if no active rules for (doctype, event). Fast-path with watched_fields if available.
3. **Eligibility** — For each candidate rule:
    - Active check
    - Event match
    - Trigger condition evaluation via `frappe.safe_eval(compiled_expression)` with SafeFrappeAPI
    - Compile-time validation ensures `compiled_expression` exists (fallback to `trigger_condition` deprecated)
4. **Dispatch** — For eligible rules:
    - Synchronous: `RuleEngine.execute()` in current transaction
    - Asynchronous: `frappe.enqueue` → `RuleCoordinator.run_rule_background`
5. **Engine Execution** (`RuleEngine._execute_graph`):
    - Determine start node (Entry Action or node with no incoming edges)
    - Iterative traversal (max 1000 iterations total)
    - Per-node visit counting (max 100 visits per node → CycleDetectedError)
    - Handler lookup: `HandlerRegistry.get(normalize_action_type(action_type))`
    - Handler `execute(action, context, engine)` → `(result, next_action_id)`
    - Post-process via `_post_process_action_result()`:
      - Output mapping (`output_mapping`)
      - Return variable storage + type validation
      - Return keys schema validation
      - Mutation mode application (`ContextManager.apply_mutation`)
    - Advance to `next_step_if_true` unless error dictates alternate path
6. **Error Handling** (per-action `on_error`):
    - `Continue` → log warning, follow `next_step_if_true`
    - `Retry` → exponential backoff (2^attempt sec), up to `retry_count`, re-raise if exhausted
    - `Rollback` → `frappe.db.rollback(savepoint=...)`, re-raise
    - `Escalate` → log and re-raise immediately
    - Default → log and raise
7. **Completion** — Persist execution log via `frappe.enqueue` (unless dry_run/test_mode)
    - Build `last_execution_payload` with path_trace, vars, messages
    - Update `rule.last_error` on failure (if not dry/test)

## Handler Strategy Pattern
- Base class: `ActionHandler` with `execute(action, context, engine) → (result, next_id)`
- Registry: `HandlerRegistry._handlers` lazily populated on first `get()`
- Built-in handlers:
  - `ConditionHandler` — evaluate `compiled_expression`, branch true/false
  - `ProcessHandler` — invoke `Process.execute()`, retry with timeout
  - `StopHandler` — terminal (Success) or raise (Error)
  - `WaitHandler` — `time.sleep(duration)`
  - `SetValueHandler` — compute `value_template`, apply `mutation_mode`
  - `NotifyHandler` — Toast/System/Email/System Notification/Provider
  - `QueryRecordsHandler` — frappe.get_all/frappe.get_value/etc, aggregate ops
  - `DocumentActionHandler` — Create/Update/Delete/Create ToDo/Add Comment
  - `SubRuleHandler` — nested `RuleCoordinator.execute_rule()` with context merging
  - `LoopHandler` — iterate with `item_alias`, body path, return path
  - `SwitchHandler` — evaluate expression, dispatch to matching case

## Cycle Detection
- Node visit counter (per-node limit 100)
- Total iteration limit 1000
- Reentry guard for same (doc, event) within request (prevents recursive trigger loops)

## Safety Features
- `SafeFrappeAPI` — whitelisted read-only methods only (no write/db commit/rollback)
- Timeout protection — per-rule `max_execution_time` with `time_limit` context
- Transaction boundaries — savepoints per-action when `transactional` flag set
- Permission checks — skip_for_roles (rule-level), skip_permissions (action-level with audit)
- Input validation — JSON schema for Process `config`, return type coercion

