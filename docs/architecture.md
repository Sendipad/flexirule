# FlexiRule Architecture

## System Overview
FlexiRule = Visual rule builder + Graph orchestration engine + Process adapter system
- Built for Frappe v15+ with Vue 3 frontend

## Architecture Layers

### 1. Presentation Layer (Vue 3 + VueFlow)
- Rule Builder UI
- Dynamic schema-driven forms
- Pinia state management (5 stores)
- Real-time validation

### 2. API Layer (`flexirule.ruleflow.api`)
- Whitelisted endpoints for all CRUD + execution
- Permission gating via `require_builder_access`
- Structured error responses

### 3. Domain Layer — Core Engine Components
- **RuleCoordinator** — Entry point, registry builder, event dispatcher, cache manager
- **RuleEngine** — Graph executor, handler invoker, error/recovery, logging
- **HandlerRegistry** — Strategy pattern for action type handlers (plug-in architecture)
- **ConditionCompiler** — JSON AST → Python compiled expression compiler
- **FieldResolver** — Safe dot-path/bracket-path resolution for context variables
- **ContextManager** — Variable lifecycle, return type validation, mutation modes
- **GraphService** — Graph initialization, node config schema generation, validation
- **ProcessRegistry** — Central Process/Operation metadata cache
- **ValidationService** — Rule/Node validation pipeline

### 4. Persistence Layer
- Rule DocType (metadata + actions child table + visual_data)
- Rule Action child table (compiled_expression, config, connections)
- Process DocType (file-backed, .py/.js generation)
- Process Operation child table (operation metadata)
- Rule Execution Log (async-persisted)
- Rule Version hooks (history tracking)

## Key Subsystems
- **Runtime Registry** — Compiled per-request + Redis + DB fallback
- **Compiled Expressions** — `condition_json` → `compiled_expression` via `ConditionCompiler.compile_node()`
- **Permission Model** — Role-based execution skip + per-action permission audit
- **Error Policy** — `on_error` modes: Stop (default), Continue, Retry (exponential backoff), Rollback (savepoint), Escalate
- **Transaction Model** — Per-action savepoints for rollback without aborting full transaction
- **Execution Tracing** — Full path trace with timestamps, status, inputs/outputs; enqueued to Rule Execution Log

## Integration Points
- `doc_events` hooks (via `RuleCoordinator.execute_rules`)
- Scheduler (via `frappe.enqueue` for async rules)
- Background workers (async execution + log persistence)
- Real-time cache clear events (`flexirule_cache_clear`)

