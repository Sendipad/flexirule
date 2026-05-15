# Trigger System

The FlexiRule Trigger System determines when a rule should begin its execution. It is managed by the `RuleCoordinator`, which acts as a high-performance dispatcher integrated into the Frappe lifecycle.

## Trigger Types

FlexiRule supports three primary trigger types, each serving a different architectural purpose:

### 1. DocType Event

This is the most common trigger type. It hooks directly into Frappe's `doc_events`.

- **Standard Hooks**: Supports all standard Frappe hooks (e.g., `Before Insert`, `Before Save`, `Validate`, `On Submit`, `On Change`, `On Trash`).
- **Optimization**: Uses `watched_fields` to avoid executing rules if unrelated fields are modified.
- **Context**: Provides the current `doc` and `old_doc` (state before save) to the execution engine.

### 2. Scheduler Event

Used for background, time-based automation.

- **Mechanism**: Integrated with Frappe's scheduled tasks.
- **Context**: Since it's not tied to a specific document event, these rules typically start with a `Query Records` action to find the documents they need to process.

### 3. Callable Event (Sub-Rules)

These rules do not trigger automatically. Instead, they are designed to be called by other rules.

- **Exposability**: Must have the `exposed_as_subrule` flag enabled to be visible in the `Sub-Rule` action picker.
- **Priority**: Always has a priority of `0` because execution is determined by the caller.

---

## The Rule Coordinator

The `RuleCoordinator` is responsible for identifying and qualifying rules for execution.

### Dispatching Logic

When a document event occurs, the Coordinator:

1.  **Fast Lookup**: Queries a request-local cache (then Redis) for rules matching the `DocType` and `Event`.
2.  **Pruning**: Checks if the rule's `watched_fields` intersect with the fields changed in the current transaction.
3.  **Eligibility**: Evaluates the `compiled_expression` of the rule.
4.  **Execution**: Dispatches the rule to the `RuleEngine` (Synchronous) or enqueues it (Asynchronous).

### Runtime Registry & Caching

To maintain high performance, FlexiRule uses a layered caching strategy for rule metadata:

- **Level 1 (Request)**: `frappe.local` storage for the duration of a single request.
- **Level 2 (Redis)**: A global `flexirule_runtime_registry` in Redis.
- **Level 3 (Database)**: Rebuilds the registry from the `Rule` DocType on cache miss or manual clear.

---

## Trigger Conditions

Trigger conditions are written visually in the builder and compiled into pure Python.

### Features

- **Field Access**: Access fields via `doc.status` or deep paths like `doc.items.0.qty`.
- **Change Detection**: Compare `doc` vs `old_doc` (e.g., `doc.status != old_doc.status`).
- **Safety**: Evaluation is strictly read-only via `SafeFrappeAPI`.

### Performance Note

Trigger conditions are designed to be "ultra-fast." They are evaluated before the full `RuleEngine` is initialized to ensure that rules that don't meet the criteria consume minimal resources.
