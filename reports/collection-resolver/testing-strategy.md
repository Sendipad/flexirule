# Collection Resolver: Testing Strategy

## 1. Verified Unit Testing Matrix (`flexirule/ruleflow/tests/test_value_resolvers_complex.py`)

A comprehensive test class `TestCollectionResolver` will test all operations, edge cases, and safety guards.

### 1.1 Operation Unit Tests
- **`test_collection_count`**:
  - Test total count on non-empty collection (`doc.items`).
  - Test filtered count matching a subset of rows (`qty > 10`).
  - Test count on empty collection `[]` returning `0`.
- **`test_collection_any`**:
  - Test returning `True` when at least one row matches condition.
  - Test returning `False` when zero rows match condition.
  - Test short-circuit behavior (verifying iteration stops early).
- **`test_collection_all`**:
  - Test returning `True` when all rows match condition.
  - Test returning `False` when at least one row fails condition.
  - Test vacuous truth (`True`) on empty collection `[]`.
- **`test_collection_first_and_find`**:
  - Test retrieving first item matching condition.
  - Test returning `None` when no items match.
- **`test_collection_filter`**:
  - Test filtering list of rows by condition, returning matching row dicts.
  - Test filtering returning empty list `[]` when no rows match.
- **`test_collection_pluck`**:
  - Test extracting list of field values (e.g. `item_code`).
  - Test behavior with missing fields in some row dicts.
- **`test_collection_unique`**:
  - Test extracting unique list of field values while preserving order.

---

## 2. Edge Case & Data Type Coverage
- **Missing / Null Context Fields**: Null collection path, null row fields, missing dictionary keys.
- **Data Types**: String equality, numeric comparisons, boolean checks, date comparisons on row fields.
- **Row Context Isolation**: Ensure `row.qty` in condition evaluation resolves row field without conflicting with `doc.qty` or `vars.qty`.

---

## 3. Security & Limit Testing
- **Non-Eval Verification**: Assert condition evaluation uses `ConditionEvaluator` and rejects string expressions or Python injection attempts.
- **Iteration Limit Guard Test**: Pass a list of 10,001 items and verify `MethodExecutionError` is raised.

---

## 4. Regression Testing
- Verify existing `ChildAggregationResolver` tests in `test_value_resolvers_complex.py` pass without regression.
- Verify `LoopHandler` tests in `test_engine.py` pass without regression.
- Verify existing `ConditionEvaluator` tests pass without regression.
