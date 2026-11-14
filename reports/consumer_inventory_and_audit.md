# Canonical Condition and FlexValue Consumer Inventory

**Reviewed:** 14 November 2026  
**Code baseline:** `f53818bbe068e7d3c46030108112eec6e3706b7b` plus the follow-up fixes in this PR  
**Scope:** Active condition/FlexValue producers, validators, execution paths, and legacy compatibility modules in FlexiRule.

## 1. Active consumer inventory

| Consumer | Current integration | Status and boundary | Regression coverage |
|---|---|---|---|
| Rule trigger condition | `Rule.compile_conditions()` → `validate_condition_node()`; runtime trigger evaluation through the canonical evaluator | Canonical direct-node payload is validated with the owning Rule DocType. Legacy payloads remain behind the explicit legacy adapter. | `test_rule.py`, `test_canonical_condition_evaluator.py` |
| `ConditionStep.vue` | `CanonicalConditionBuilder.vue` | Uses the canonical contract, current Rule DocType, and deferred validation on explicit save. | `canonical_condition_deep_review.test.mjs`, `production_readiness_scenarios.test.mjs` |
| Condition action | `CanonicalConditionBuilder.vue` → `ConditionHandler` → canonical evaluator | Canonical conditions are validated on Rule save and evaluated from prepared plans; legacy compiled expressions remain a separate compatibility path. | `test_rule.py`, `test_canonical_condition_evaluator.py` |
| `AssignmentConfig.vue` run-if | `CanonicalConditionBuilder.vue` stored under `when_condition` | Canonical-only guard contract; Rule validation and runtime preflight use the same strict compiler and the Rule DocType. All rows are preflighted before staged changes are committed. | `test_assignment_condition_guards.py`, `test_assignment_lifecycle` |
| `CollectionResolver.vue` | `CanonicalConditionBuilder.vue` with `collectionSource` and parent DocType | Migrated from the old builder. Child DocType metadata is resolved from the parent's Table field and passed to backend `api.validate_condition` for `row`-scope validation. | `test_collection_resolver.py`, `collection_metadata_validation.test.mjs` |
| `CanonicalConditionLeaf.vue` | `FlexValueControl.vue` for both operands | Fieldtype metadata drives the operand descriptor. Link options and link filters are retained; Check values serialize as Frappe-compatible integer 0/1. | `canonical_condition_adapter.test.mjs`, `flex_value_control_lifecycle.test.mjs` |
| Membership operators (`in`, `not_in`) | Native MultiSelect controls / canonical list FlexValues | Link membership keeps the target DocType and filter metadata; Check membership uses integer 0/1 choices. | `static_presentation.test.mjs`, `flexvalue_p1_p2_verification.test.mjs` |
| `TextGeneratorControl.vue` | `CanonicalConditionBuilder.vue` and canonical template AST | Conditional segments compile to an isolated condition registry. Loop alias DocType metadata is now persisted with each registry entry and restored at render time, including mapping-backed child rows. | `test_text_generator_canonical_conditions.py` |
| `FlexValueControl.vue` and resolver strategies | Shared FlexValue contract plus registered resolver strategies | Nested resolver validators are awaited by the owner. Resolver execution remains controlled by the consumer contract and backend allow-list. | `test_unified_flexvalue.py`, `flexvalue_control_ux_refactor.test.mjs` |
| `api.validate_condition` | `validate_condition_node()` | Read-only validation API supports `collection_source` and derives row DocType from trusted Frappe metadata. | `test_canonical_condition_evaluator.py` |
| `api.validate_rule_document` / shared validation service | `Rule.compile_conditions()` then `validate_rule_definition()` | Both full-rule and single-action handler validation now receive the owning Rule context so metadata-aware handlers can resolve the correct DocType. | `test_rule.py` |
| `SubRuleHandler` | Canonical eligibility evaluation | Caller Rule and document metadata are propagated into child contexts, including callers without an eligibility condition. | `test_sub_rule_contract.py` |
| Backend `CollectionResolver` | `prepare_condition()` / `evaluate_prepared_condition()` | Child-row metadata and the bounded evaluation context are retained for mapping-backed rows and nested predicates. | `test_collection_resolver.py`, `test_canonical_condition_evaluator.py` |
| Frappe native `Check` and `Duration` fields | Typed boundary in canonical evaluator and FlexValue parser | Check is integer 0/1; Duration is integer seconds. Neither is conflated with Python bool or `datetime.time`. | `test_canonical_condition_evaluator.py`, `test_unified_flexvalue.py` |

## 2. Legacy compatibility boundary

The older condition-builder components and Python condition compiler/evaluator remain in the repository as deprecated compatibility code. They should not be deleted as part of this refactor. Before removal, verify repository-wide imports, server-side callers, saved payload formats, and the read-only migration inventory. Do not treat the continued presence of legacy files as evidence that active consumers still use them.

## 3. Verified Frappe-native semantics

- Frappe Check controls read/write integer `0` or `1`; canonical evaluation must preserve this representation instead of returning Python booleans for Check DocFields.
- Frappe Duration fields represent seconds as an integer. They are ordered numeric values, not clock-time values.
- Link search and DocType metadata should continue to use Frappe's native metadata and Link control mechanisms instead of introducing a parallel lookup implementation.

## 4. Remaining release checks

- Run the read-only condition inventory against a representative site/export and review ambiguous legacy payloads before defining any write migration.
- Keep a complete consumer-by-consumer execution matrix for trigger eligibility, Condition routing, Sub-Rule eligibility, Assignment guards/no partial mutation, collection predicates, Text Generator loop aliases, and preview/helper routes.
- Treat performance decisions as unestablished until clean-checkout benchmark distributions are compared against an agreed production workload and latency budget.
- Continue adversarial tests for payload depth/size, cyclic input, nested collection budgets, and metadata changes after plan-cache hits.
- Keep resolver families deny-by-default until each enabled family has reviewed output typing, permissions, resource budgets, and regression coverage.
