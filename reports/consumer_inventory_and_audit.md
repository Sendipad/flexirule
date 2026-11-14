# Comprehensive Condition and FlexValue Consumer Inventory

**Date:** 11 November 2026
**Scope:** Complete inventory of all active and legacy condition and FlexValue consumers across FlexiRule frontend and backend.

## 1. Consumer Inventory Matrix

| Consumer Component / Module | Type / Role | Current Implementation | Migration Status | Remaining Gaps / Action Needed | Test Coverage |
|---|---|---|---|---|---|
| `ConditionStep.vue` | UI: Rule Entry Conditions | `CanonicalConditionBuilder.vue` | Fully Migrated | Add `showValidation` deferred validation prop & expose `caller` context fields for Callable Event trigger type | `production_readiness_scenarios.test.mjs`, `canonical_condition_deep_review.test.mjs` |
| `AssignmentConfig.vue` | UI: Assignment `when_condition` | `CanonicalConditionBuilder.vue` | Fully Migrated | Connect `showValidation` to suppress draft errors until explicit save/validation | `test_assignment_condition_guards.py`, `action_config_validation.test.mjs` |
| `CollectionResolver.vue` | UI: Child table row condition filter | Legacy `ConditionBuilder.vue` | **Needs Migration** | Replace with `CanonicalConditionBuilder.vue`, resolve child DocType as metadata context, validate child fields (`row.*`), persist canonical AST | `test_collection_resolver.py`, `flexvalue_p1_p2_verification.test.mjs` |
| `TextGeneratorControl.vue` | UI: Rich-text conditional template segments | `CanonicalConditionBuilder.vue` | Fully Migrated | Connect `showValidation` deferred validation | `test_text_generator_canonical_conditions.py`, `config_save_lifecycle.test.mjs` |
| `CanonicalConditionLeaf.vue` | UI: Left/right condition operand control | `FlexValueControl.vue` & direct canonical AST | Fully Migrated | Support Check 0/1 integer serialization, Link filter forwarding, Dynamic Link resolution, deferred validation | `canonical_condition_adapter.test.mjs`, `flex_value_control_lifecycle.test.mjs` |
| `MultiSelectList.vue` | UI: Multi-select for membership operators (`in`, `not_in`) | Native list selector | Fully Migrated | Ensure `filters` prop is forwarded to `search_link_options` | `static_presentation.test.mjs` |
| `QueryRecordsConfig.vue` & `FilterLeaf.vue` | UI: Query Records filters | Query Filter Builder (`FilterLeaf.vue`, `FlexValueControl.vue`) | Fully Migrated | Uses canonical query filter serialization | `query_filter_serializer.test.mjs`, `test_query_records_canonical_filters.py` |
| `ValueResolverControl.vue` & strategies | UI: Resolver configuration popover | Registered strategies (`CollectionResolver`, `DateTimeResolver`, etc.) | In Progress | Connect deep validation (`validateDeep`) for nested canonical condition validation | `test_unified_flexvalue.py`, `test_value_resolvers_complex.py` |
| `SubRuleHandler` (`sub_rule.py`) | Backend: Sub-rule condition evaluation | Canonical condition detection & evaluation | Fully Migrated | Propagate caller metadata (`caller.doctype`, `caller.name`, etc.) into context even when condition is absent | `test_sub_rule_contract.py` |
| `api.validate_condition` | Backend API: Condition validation | `validate_condition_node` | Fully Migrated | Support `collection_source` to resolve child DocType metadata for `row` scope | `test_canonical_condition_evaluator.py` |
| `CollectionResolver` (`value_resolver.py`) | Backend Resolver: Child record operations | Canonical `prepare_condition` & `evaluate_prepared_condition` | Fully Migrated | Strictly fail-closed on malformed conditions, child row context isolation | `test_collection_resolver.py` |

## 2. Deprecation Summary
All legacy files (`ConditionBuilder.vue`, `SimpleCondition.vue`, `ConditionGroupUI.vue`, `ConditionNode.vue`, `CollectionUI.vue`, `ConditionCompiler`, `ConditionEvaluator`) remain marked as deprecated and are not deleted, ensuring backward compatibility while having zero active dependencies from current consumers.
