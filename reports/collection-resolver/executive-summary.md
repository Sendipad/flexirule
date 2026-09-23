# Executive Summary: FlexiRule Collection Resolver Design

## 1. Why Collection Resolver is Needed
FlexiRule rules frequently need to evaluate or extract values from Frappe child-table collections (e.g., `doc.items`, `doc.taxes`, `doc.payments`). Prior to Collection Resolver, users had to choose between two incomplete options:
1. **Child Aggregation Resolver (`child_aggregation`)**: Limited to simple numeric sums/averages/counts across all rows without any row-level filtering or predicate matching.
2. **Loop Action (`Loop`)**: Required heavy process-graph looping and mutable state variable updates simply to check a predicate (e.g., "does any item have qty > 100?") or extract a list of codes.

Collection Resolver bridges this gap by providing an inline, declarative, side-effect-free Value Resolver strategy for collection querying, filtering, checking, and extraction.

---

## 2. Exact Beta Scope
The Beta implementation focuses on practical, high-value collection querying without modifying or redesigning the existing Value Resolver or Condition framework.

- **Scope**: Single-level collection querying (Frappe child tables and list variables) with optional condition evaluation per row.
- **Out of Scope (Deferred)**: Multi-level nested collections (`items[].taxes[]`), mutable collection transformations (in-place row mutations), and complex multi-pass pipeline chaining.

---

## 3. Recommended Operations for Beta
| Operation | Purpose | Input | Output | Result Type |
| :--- | :--- | :--- | :--- | :--- |
| **`count`** | Count total rows or rows matching a condition | Source (+ Condition) | Row count | `integer` |
| **`any`** | Check if at least one row matches condition | Source + Condition | Truth value | `boolean` |
| **`all`** | Check if all rows match condition | Source + Condition | Truth value | `boolean` |
| **`first`** | Retrieve the first row (or first row matching condition) | Source (+ Condition) | Row dict / `None` | `dict \| null` |
| **`last`** | Retrieve the last row in collection | Source | Row dict / `None` | `dict \| null` |
| **`find`** | Semantic alias for `first` with a required condition | Source + Condition | Row dict / `None` | `dict \| null` |
| **`filter`** | Extract sub-collection of matching rows | Source + Condition | Filtered array | `list[dict]` |
| **`pluck`** | Extract array of specific field values from rows | Source + Field | Value array | `list[Any]` |
| **`unique`** | Extract unique array of specific field values | Source + Field | Unique value array | `list[Any]` |

---

## 4. Explicitly Deferred Operations
- **`map` / `transform` (Arbitrary Row Expressions)**: Deferred to avoid introducing complex row-level expression mapping in Beta.
- **`sort` / `reverse`**: Deferred; row order defaults to Frappe child table document order (`idx`).
- **`groupby` / `partition`**: Deferred due to high state complexity.
- **Nested Collections (`items[].taxes[]`)**: Deferred; Beta supports top-level child table arrays.

---

## 5. Relationship with Loop Action
- **Loop Action**: Execution control flow handler. Manages iteration state (`_loops`), executes child graph nodes, performs document mutations or external API calls for each row.
- **Collection Resolver**: Pure expression evaluator. Side-effect free, runs synchronously inside `ValueResolver.compile()`, derives a single value or filtered array for assignment or condition evaluation.

---

## 6. Relationship with Child Aggregation
- **Child Aggregation (`child_aggregation`)**: Optimized numeric aggregator (`sum`, `avg`, `count`) across all rows.
- **Collection Resolver (`collection`)**: Adds predicate matching (`where`), non-numeric operations (`find`, `filter`, `pluck`, `unique`), and boolean checks (`any`, `all`).
- **Coexistence**: Unfiltered numeric aggregations remain handled by `child_aggregation`. Filtered aggregations can compose `filter` with `child_aggregation` or use `collection.count`.

---

## 7. Proposed JSON Contract
```json
{
  "mode": "resolver",
  "config": {
    "kind": "collection",
    "operation": "any",
    "source": "doc.items",
    "condition": {
      "left": { "ref": "row.qty" },
      "op": ">",
      "right": { "value": 100 }
    },
    "target_field": null
  }
}
```

---

## 8. Required Frontend & Backend Changes
- **Backend**:
  - Add `CollectionResolver(CompiledResolver)` class in `flexirule/ruleflow/core/value_resolver.py`.
  - Register `kind == "collection"` in `ValueResolver.compile_resolver_config`.
  - Utilize existing `ConditionEvaluator` for row-level evaluation (`doc` + `row` context).
- **Frontend**:
  - Register `"collection"` strategy in `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`.
  - Create `CollectionResolver.vue` control component.
  - Update `formula_registry.js` and `getAllowedBuilderKinds()`.

---

## 9. Testing Requirements
- Unit tests in `flexirule/ruleflow/tests/test_value_resolvers_complex.py` for all 9 operations.
- Edge case testing: empty collections, `None` fields, missing keys, row context isolation.
- Security tests: preventing arbitrary code injection in row conditions.
- Performance tests: benchmark 10, 100, 1,000, and 10,000 row collections.

---

## 10. Risks & Mitigation
- **Risk 1: Deep recursion / huge collections causing DoS**:
  - *Mitigation*: Impose a strict iteration limit (e.g., 10,000 rows max) with early break.
- **Risk 2: Ambiguity in field path resolution (`doc.qty` vs `row.qty`)**:
  - *Mitigation*: Enforce explicit `row.` prefixing in `ConditionEvaluator` and fallback to `row.get(fieldname)` when in row scope.
