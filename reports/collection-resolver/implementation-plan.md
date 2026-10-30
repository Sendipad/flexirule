# Collection Resolver: Implementation Plan

This roadmap outlines the exact, phased steps for implementing the Collection Resolver after architectural design approval.

---

## Phase 1: Backend Strategy Implementation

1. **Implement `CollectionResolver` Class**:
   - Location: `flexirule/ruleflow/core/value_resolver.py`
   - Implement `CollectionResolver(CompiledResolver)` supporting core operations: `count`, `any`, `all`, `first`, `filter`, `pluck`, `unique` (and mapping UI alias `find` -> `first`).
   - Incorporate `ConditionEvaluator` delegation and the 10,000 row iteration exception guard.
2. **Register Factory Kind in Compiler**:
   - In `ValueResolver.compile_resolver_config(config)` at line 465:
     Add branch for `kind == "collection"`.

---

## Phase 2: Backend Test Suite

1. **Add Test Class `TestCollectionResolver`**:
   - Location: `flexirule/ruleflow/tests/test_value_resolvers_complex.py`
   - Implement unit tests covering all 8 operations/aliases, null/empty collections, row context isolation, and limit exception guards.
2. **Run Python Test Suite**:
   - Run `bench run-tests --module flexirule.ruleflow.tests.test_value_resolvers_complex`.

---

## Phase 3: Frontend Control & Integration

1. **Create `CollectionResolver.vue` Component**:
   - Location: `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/CollectionResolver.vue`
   - Build UI inputs for `source`, `operation`, `target_field`, and embedded row filter condition using `ComboBoxControl` and `SelectControl`.
2. **Register Strategy in Resolver Strategy Registry**:
   - In `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`:
     Add `registerStrategy("collection", ...)` definition.
3. **Update Formula Registry & Commands**:
   - In `flexirule/public/js/flexirule/core/formula_registry.js`:
     Add slash commands and update `getAllowedBuilderKinds()`.

---

## Phase 4: Verification & Pre-Commit Audit

1. **Frontend Verification**:
   - Verify UI rendering in Rule Builder, Tiptap token creation, and JSON serialization.
2. **Pre-Commit Checks**:
   - Run `pre-commit run --all` across the repository.
