# Phased Architecture Remediation Plan

## Executive Summary

This remediation plan outlines a phased, zero-downtime implementation roadmap for evolving FlexiRule's Value Resolver architecture into the proposed 4-family taxonomy (**Transform**, **Collection**, **Retrieval**, **Environment**).

All phases preserve 100% backward compatibility for existing serialized rule configurations.

---

## 1. Roadmap Overview

```
+-----------------------------------------------------------------------------------+
| PHASE 1: Enhanced CollectionResolver (Add Numeric Aggregations sum/avg/min/max)  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| PHASE 2: Backend Family Registry & In-Memory Alias Dispatcher                     |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| PHASE 3: Frontend Strategy Grouping in ValueResolverControl & Slash Commands      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| PHASE 4: Deprecation Warnings & Utility Refactoring (FieldResolver Delegation)    |
+-----------------------------------------------------------------------------------+
```

---

## 2. Phase-by-Phase Execution Details

### Phase 1: Extend `CollectionResolver` Capabilities
- **Objective**: Add `sum`, `avg`, `min`, and `max` operations directly to `CollectionResolver`.
- **Impact**: Enables filtered aggregations (e.g. sum of item amounts where rate > 100) and unlocks complete functional equivalence with `child_aggregation`.
- **Target Files**:
  - `flexirule/ruleflow/core/value_resolver.py` (`CollectionResolver.resolve`)
  - `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/CollectionResolver.vue`
- **Migration Risk**: Low (purely additive).

### Phase 2: Backend Hierarchical Dispatcher & Legacy Routing
- **Objective**: Introduce family wrapper classes (`TransformFamily`, `CollectionFamily`, `RetrievalFamily`, `EnvironmentFamily`) in `value_resolver.py` while maintaining a legacy lookup dictionary for old `kind` identifiers (`child_aggregation`, `date_formula`, etc.).
- **Target Files**:
  - `flexirule/ruleflow/core/value_resolver.py` (`ValueResolver.compile_resolver_config`)
- **Migration Risk**: Low (100% backward compatible).

### Phase 3: Frontend Category Grouping & UI Optimization
- **Objective**: Update `ValueResolverControl.vue` to display strategy buttons organized into 4 collapsible/tabbed Family accordions instead of a flat list of 10 buttons. Update `formula_registry.js` category mappings.
- **Target Files**:
  - `flexirule/public/js/flexirule/rule_builder/controls/ValueResolverControl.vue`
  - `flexirule/public/js/flexirule/core/formula_registry.js`
- **Migration Risk**: Low (pure UI UX enhancement).

### Phase 4: Utility Refactoring & Non-Resolver Consolidation
- **Objective**: Refactor `FieldResolver.aggregate_child_table()` in `flexirule/ruleflow/utils/field_resolver.py` to delegate to `ValueResolver.compile()`.
- **Target Files**:
  - `flexirule/ruleflow/utils/field_resolver.py`
- **Migration Risk**: Medium (requires running regression test suite `bench --site test_site run-tests --app flexirule`).
