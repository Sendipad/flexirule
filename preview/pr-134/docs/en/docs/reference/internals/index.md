# Internals<no value>

# Core Engine Internals

This document covers the low-level management of the FlexiRule engine.

## Runtime Registry Resolution

To achieve sub-millisecond rule lookup times, FlexiRule uses a layered **Compiled Runtime Registry**.

### The Resolution Chain

1.  **Request Cache**: `frappe.local.flexirule_runtime_registry`. Valid for the current HTTP request/Job.
2.  **Global Cache**: Redis key `flexirule_runtime_registry_v2`. Valid across all web workers.
3.  **Database**: Rebuilt from the `Rule` DocType.

### Layered Hydration

When a rule is requested, the system checks Level 1. If missing, it checks Level 2 and populates Level 1. If Level 2 is also missing, it performs a SQL query, compiles all active rules, and hydrates both Level 2 and Level 1.

---

## Distributed Cache Invalidation

Because FlexiRule can run in multi-server or multi-worker environments, cache consistency is critical.

### Event-Based Invalidation

When a Rule is saved, deleted, or its status changes:

1.  **Local Flush**: The current worker clears its `frappe.local` cache.
2.  **Redis Flush**: The Redis key is deleted.
3.  **Realtime Broadcast**: A `flexirule_cache_clear` event is published via Frappe's Realtime (Socket.io) system.
4.  **Global Sync**: Other active web workers receive the event and clear their request-local caches for the next request.

---

## Transactional Integrity

### Per-Action Savepoints

The engine maintains a granular approach to transactions. Instead of a single "all-or-nothing" rule execution, each action can be its own transactional unit:

- **Savepoint Naming**: `flexirule_action_{action_id}`.
- **Savepoint Logic**: Enables the "Rollback" error policy, allowing one node to fail and revert its specific database changes while the rule execution continues or escalates gracefully.

---

## Watch Fields Optimization

The coordinator uses a bitmask-like approach for filtering rules:

1.  **Field Diffing**: Upon `before_save`, the engine computes the set of changed field names.
2.  **Intersection**: It compares this set with the rule's `watched_fields`.
3.  **Fast Skip**: If the intersection is empty, the rule is never initialized, saving CPU and memory cycles.
