# Trigger System Deep Dive

## Trigger Types
1. **DocType Event** — Primary trigger; hooks into `frappe.doc_events`
    - Events supported: all standard Frappe hooks (Before Naming through After Print)
    - Safety: `Set Value` and `writes_to == "Document"` restricted to after-events only (validated in `check_eligibility`)
    - Watched fields: optional comma-separated list for change-based filtering at dispatch time (optimization)
    - Filtering also via `trigger_condition`/`compiled_expression` (executed after eligibility check)

2. **Scheduler Event** — Fired by Frappe scheduler
    - `trigger_type = "Scheduler Event"`
    - No document context; rule must fetch its own data
    - Cannot rely on `doc` in trigger condition
    - Currently implemented via rule scheduler integration (future)

3. **Callable Event** — Sub-rules
    - `trigger_type = "Callable Event"`
    - `exposed_as_subrule = 1` required
    - Invoked via `Sub-Rule` action with `skip_conditions` option
    - Priority forced to `0` (no auto-execution from events)

## RuleCoordinator — The Dispatcher
- `execute_rules(doc, event_name)` — Hook entry point (frappe.doc_events)
   - Skips during `frappe.flags.in_import` or `in_migrate`
   - Delegates to `execute_rules_from_event()`
- `execute_rules_from_event()`
   - Gets runtime specs from `_get_event_runtime(doctype, event)` (from registry)
   - Reentrancy guard: `_event_reentry_guard` prevents recursive triggers on same (doc, event) within request
   - Fetches `old_doc` once
   - Applies `_passes_watched_field_filter(rule_spec, doc, event)` — fast change detection before eligibility
   - Calls `check_eligibility()` for each rule
   - Executes valid rules with `execute_single_rule()`
- `check_eligibility()` — strict v1 contract
   - Active check
   - Event match (unless `skip_event_check`)
   - Execution mode (log only; async handled by executor)
   - **Trigger condition evaluation** — `frappe.safe_eval(compiled_expression, eval_globals)`
     - `eval_globals` includes: `doc`, `old_doc`, `vars`, `frappe` (SafeFrappeAPI), `caller`, `rule`, `doctype`, `is_submittable`, `has_field`, `get_meta`, `resolve`, `check_link_match`, `True/False/None`
     - **Security:** SafeFrappeAPI blocks write operations; only read-safe methods exposed
   - Returns `(bool, reason)` tuple
- `get_applicable_rules()` — backward-compatible map accessor, handles stale cache

## Registry & Caching
- `get_runtime_registry()` — layered cache:
  1. `frappe.local.RULE_RUNTIME_REGISTRY` (request-local)
  2. `frappe.cache.get_value("flexirule_runtime_registry_v2")` (Redis; 5-minute TTL if configured)
  3. DB rebuild via `_build_runtime_registry()`
- Registry structure:
   ```python
   {
     "cache_version": 2,
     "rules": {rule_name: {name, doctype, event, priority, compiled_expression, execution_mode, debug_mode, watched_fields, compiled_dependencies}},
     "doctype_event_map": {doctype: {event: [rule_name, ...]}}
   }
   ```
- Cache invalidated on rule changes via `should_rebuild_registry_for_rule_change()`
   - Rebuild triggered on active DocType Event rule insert/update/delete affecting runtime signature

## Async Execution
- If `rule.execution_mode == "Asynchronous"` and `doc` is saved (not `__islocal`):
   - `frappe.enqueue("flexirule.ruleflow.coordinator.RuleCoordinator.run_rule_background", ...)`
   - Queue: `default`
   - Timeout: `rule.max_execution_time or 300`
   - Background entry point re-fetches rule + doc and creates new `RuleEngine`

## Optimization: Watched Fields
- Optional `rule.watched_fields` (comma-separated or list)
- Extracted from `compiled_expression` automatically via regex patterns (fallback)
- Filter applied at dispatch time: `_passes_watched_field_filter()`
- Computes `changed_fields` once per doctype/name via `doc.get_doc_before_save()` comparison