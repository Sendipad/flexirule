---
title: "API"
weight: 10
---

# API Reference

FlexiRule provides a comprehensive set of whitelisted backend methods for programmatic interaction, rule execution, and builder integration.

## Rule Execution APIs

### `test_rule`

Executes a rule against a document for testing purposes. Works for draft and inactive rules.

- **Parameters**:
    - `rule_name`: Name of the Rule.
    - `doctype` / `docname`: Target document.
    - `document_json`: Transient document data (alternative to docname).
    - `dry_run` (bool): If true, rolls back changes after execution.
    - `skip_log_enqueue` (bool): If true, does not persist logs.
    - `save_log` (bool): Forces log persistence regardless of dry_run.
- **Returns**: Execution payload including `status`, `path_trace`, `vars`, and legacy `context_snapshot`.

### `execute_rule`

The primary API for manual or programmatic rule execution.

- **Parameters**:
    - `rule_name`: Name of the Rule.
    - `context` (dict): Initial variable state.
    - `dry_run` (bool): Execution safety flag.

---

## Lifecycle & Management

### `transition_rule`

Moves a rule through its lifecycle states.

- **Statuses**: `Draft`, `Active`, `Disabled`, `Archived`.
- **Note**: Transitioning to `Active` triggers a full validation check.

### `validate_rule_document`

Performs deep validation of a rule's graph, configuration, and conditions.

- **Modes**: `full` (for activation), `draft` (partial check), `node` (single action).

### `clone_rule` / `amend_rule`

Creates a copy of an existing rule. `amend_rule` specifically manages versioning by linking the new draft to the previous active version.

---

## Introspection & Metadata

### `get_contract_dto`

Returns the global contract for all action types, including CSS styles, required fields, and supported mutation modes. This is the source of truth for the Rule Builder.

### `get_node_config_schema`

Returns the dynamic configuration schema for a specific action type or process operation.

- **Parameters**: `action_type`, `operation`, `process_name`.

### `get_action_context_schema`

Returns a list of all variables (fields and upstream results) available to a specific node in a graph. Used for the builder's autocomplete functionality.

### `get_process_operations`

Returns a list of all operations available within a `Process`, filtered by their eligibility for the current rule's DocType.

---

## Monitoring & Utilities

### `get_rule_stats`

Computes performance metrics (success rate, average duration, execution count) from the `Rule Execution Log`.

### `get_execution_preview`

Predicts the execution path for a document by evaluating conditions without running the actual action handlers.

### `simulate_rule`

Runs the rule engine in dry-run mode and returns the execution path and variable state at each step.

### `test_action_query`

Executes a single action in isolation. Useful for auto-detecting return field schemas.

### `get_operator_config`

Returns centralized configuration for fieldtype-to-operator mappings and labels for the Condition Builder.

### `get_doctype_fields`

Returns grouped parent and child fields for a specific DocType. Supports filtering by fieldtype.

### `clear_cache`

Clears the `Runtime Registry` and request-local caches for FlexiRule.
