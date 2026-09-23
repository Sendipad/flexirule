# Executive Summary: FlexiRule Collection Resolver Design

## 1. Why Collection Resolver is Needed
FlexiRule rules frequently need to evaluate or extract values from Frappe child-table collections (e.g., `doc.items`, `doc.taxes`, `doc.payments`). Prior to Collection Resolver, users had to choose between two incomplete options:
1. **Child Aggregation Resolver (`child_aggregation`)**: Limited to simple numeric sums/averages/counts across all rows without any row-level filtering or predicate matching.
2. **Loop Action (`Loop`)**: Required heavy process-graph looping and mutable state variable updates simply to check a predicate (e.g., "does any item have qty > 100?") or extract a list of codes.

Collection Resolver bridges this gap by providing an inline, declarative, side-effect-free Value Resolver strategy for collection querying, filtering, checking, and extraction.

---

## 2. Verified Scope Against Existing Source
Following a complete source audit of FlexiRule v1.0 architecture:
- **Scope**: Single-level collection querying (`doc.<child_table>`, `vars.<variable>`, `old_doc.<child_table>`) with row-level predicate evaluation using existing `ConditionEvaluator(doc, row=r)` and `ValueResolver.compile_resolver_config()`.
- **Result Contract**: Verified that `AssignmentHandler` and `ContextManager` safely support `list[dict]`, `dict`, `list[Any]`, `int`, `bool`, and `None` when assigning to `vars` or documents.
- **Out of Scope (Deferred)**: Multi-level nested collections (`items[].taxes[]`), mutable collection transformations (in-place row mutations), and complex multi-pass pipeline chaining.

---

## 3. Verified Operations Scope
| Operation | Purpose | Input | Output | Classification |
| :--- | :--- | :--- | :--- | :--- |
| **`count`** | Count total rows or rows matching a condition | Source (+ Condition) | `integer` | Core Backend Operation |
| **`any`** | Check if at least one row matches condition | Source + Condition | `boolean` | Core Backend Operation |
| **`all`** | Check if all rows match condition | Source + Condition | `boolean` | Core Backend Operation |
| **`first`** | Retrieve the first row (or first row matching condition) | Source (+ Condition) | `dict \| null` | Core Backend Operation |
| **`filter`** | Extract sub-collection of matching rows | Source + Condition | `list[dict]` | Core Backend Operation |
| **`pluck`** | Extract array of specific field values from rows | Source + Field | `list[Any]` | Core Backend Operation |
| **`find`** | Semantic alias for `first` with required condition | Source + Condition | `dict \| null` | UI Convenience Alias |
| **`unique`** | Extract unique array of specific field values | Source + Field | `list[Any]` | Derived Operation (`pluck` + distinct) |

*Explicitly Deferred*: `last` (tail access), `map`/`transform` (row expressions), `sort`, `groupby`, and nested child-table traversals.

---

## 4. Relationship with Loop Action & Child Aggregation
- **Loop Action**: Execution control flow handler. Manages iteration state (`_loops`), executes child graph nodes, performs document mutations or external API calls for each row.
- **Child Aggregation (`child_aggregation`)**: Unfiltered numeric aggregator (`sum`, `avg`, `count`) across all rows.
- **Collection Resolver (`collection`)**: Adds predicate matching (`where`), non-numeric operations (`find`, `filter`, `pluck`, `unique`), and boolean checks (`any`, `all`).

---

## 5. Verified JSON Contract
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

## 6. Security & Guard Semantics
- **Non-Eval Execution**: All row predicates use structured JSON conditions evaluated by `ConditionEvaluator`. Python `eval`/`exec`/`lambda` are strictly forbidden.
- **Controlled Exception Guard**: If a collection exceeds 10,000 rows, `CollectionResolver` raises a controlled `MethodExecutionError` rather than silently truncating user data.

---

## 7. Verified Against Existing Source
- Verified `get_context_value` in `flexirule/ruleflow/core/value_resolver.py:12`.
- Verified `FieldResolver.resolve` in `flexirule/ruleflow/utils/field_resolver.py:12`.
- Verified `ConditionEvaluator(conditions_json)` and `evaluate(doc, row=r)` in `flexirule/ruleflow/core/evaluator.py:15`.
- Verified `ValueResolver.compile_resolver_config` in `flexirule/ruleflow/core/value_resolver.py:465`.
