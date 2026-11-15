# FlexiRule Legacy Condition Stack Deprecation Inventory

**Date:** 15 November 2026
**Scope:** Repository-wide audit of legacy vs canonical condition components, evaluators, compilers, and APIs.

## 1. Deprecated Components & Code Artifacts

| Component / Artifact | Path | Canonical Replacement | Reachable by Active Consumers? | Deprecation Status |
|---|---|---|---|---|
| `ConditionBuilder.vue` | `flexirule/public/js/flexirule/rule_builder/components/condition_builder/ConditionBuilder.vue` | `CanonicalConditionBuilder.vue` | No (all active consumers migrated) | Marked DEPRECATED |
| `SimpleCondition.vue` | `flexirule/public/js/flexirule/rule_builder/components/condition_builder/SimpleCondition.vue` | `CanonicalConditionLeaf.vue` | No | Marked DEPRECATED |
| `ConditionGroupUI.vue` | `flexirule/public/js/flexirule/rule_builder/components/condition_builder/ConditionGroupUI.vue` | `TreeBuilder.vue` / Canonical tree | No | Marked DEPRECATED |
| `ConditionNode.vue` | `flexirule/public/js/flexirule/rule_builder/components/condition_builder/ConditionNode.vue` | `CanonicalConditionLeaf.vue` | No | Marked DEPRECATED |
| `CollectionUI.vue` | `flexirule/public/js/flexirule/rule_builder/components/condition_builder/CollectionUI.vue` | `CanonicalCollectionEditor.vue` | No | Marked DEPRECATED |
| `condition_validator.js` | `flexirule/public/js/flexirule/rule_builder/components/condition_builder/condition_validator.js` | `canonical_condition_validation.mjs` / `validate_condition` API | No | Marked DEPRECATED |
| `ConditionCompiler` | `flexirule/ruleflow/core/compiler.py` | `condition_contract.validate_condition_node`, `condition_evaluator.prepare_condition` | No active consumers (retained for backward compatibility) | Marked DEPRECATED |
| `ConditionEvaluator` | `flexirule/ruleflow/core/evaluator.py` | `flexirule.ruleflow.core.condition_evaluator` | Yes — legacy-only fallback in `CollectionResolver` for non-canonical predicates | Marked DEPRECATED; fallback is retained intentionally until a separate compatibility-removal decision |
| `_compile_condition_tree` | `flexirule/ruleflow/doctype/rule/rule.py` | AST stored in segment config & evaluated via `_eval_condition` | No active consumers | Marked DEPRECATED |
| `get_operator_config` | `flexirule/ruleflow/api.py` | `flexirule.ruleflow.api.get_condition_contract` | No active UI consumers | Marked DEPRECATED |

## 2. Active Consumer Migration Status

1. **`AssignmentConfig.vue`**: Migrated from `ConditionBuilder` to `CanonicalConditionBuilder`. Direct canonical node AST persisted in `when_condition`.
2. **`CollectionResolver.vue` & `CollectionResolver` backend**: The UI uses `CanonicalConditionBuilder` with child DocType metadata. Canonical predicates are validated and prepared with `prepare_condition`, then evaluated with child DocType metadata and row-budget enforcement. The backend deliberately retains `ConditionEvaluator` only for non-canonical legacy predicates; this is a deprecated compatibility fallback, not the canonical execution path.
3. **`TextGeneratorControl.vue` & Template Segment Renderer**: Migrated to `CanonicalConditionBuilder`. Converted from generated Python expressions to Option A render-scoped canonical evaluation via `_eval_condition`, supporting loop variables, nested blocks, and error propagation.
4. **Backend Handlers (`compile_service.py`, `rule.py`, `sub_rule.py`, `condition.py`, `assignment.py`)**: Canonical payloads use the canonical validation and execution pipeline. Explicit legacy compatibility paths remain for non-canonical payloads where retained by the owning consumer; they must not reinterpret malformed canonical nodes as legacy expressions.
