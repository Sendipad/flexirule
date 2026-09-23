# FlexiRule Collection Resolver Design Review & Final Decision

This document represents the comprehensive second-pass architecture verification and design decision for adding a Collection Resolver to FlexiRule v1.0. All APIs, contracts, and execution paths cited here have been verified against the actual repository source code.

---

## 1. Current Architecture Verified From Source

The following core components of FlexiRule's resolver engine were verified from source code:

1. **`get_context_value(context: dict, path: str | None) -> Any`**
   - *Location*: `flexirule/ruleflow/core/value_resolver.py:12`
   - *Verified Behavior*: Traverses `path` against root scopes (`doc`, `vars`, `item`, `loop`, `row`). Traverses nested dictionary keys via `.get()`.
2. **`FieldResolver.resolve(doc, field_path: str) -> Any`**
   - *Location*: `flexirule/ruleflow/utils/field_resolver.py:12`
   - *Verified Behavior*: Handles dot notation, parent references, and child table fields.
3. **`ConditionEvaluator`**
   - *Location*: `flexirule/ruleflow/core/evaluator.py:15`
   - *Verified Signature*: `__init__(conditions_json: str)`, `evaluate(doc, row=None) -> bool`.
   - *Verified Behavior*: Accepts JSON string of condition nodes. Resolves left/right references against `doc` and `row` using safe built-in operators.
4. **`ValueResolver.compile_resolver_config(config: dict) -> CompiledResolver`**
   - *Location*: `flexirule/ruleflow/core/value_resolver.py:465`
   - *Verified Behavior*: Inspects `kind = config.get("kind")` and instantiates the matching `CompiledResolver` strategy.
5. **`CompiledResolver`**
   - *Location*: `flexirule/ruleflow/core/value_resolver.py:73`
   - *Verified Contract*: Base class defining `resolve(self, context: dict) -> Any`.
6. **`frappe.local.flexirule_compiled_resolvers`**
   - *Location*: `flexirule/ruleflow/core/value_resolver.py:556` in `get_compiled_resolver()`.
   - *Verified Behavior*: Caches compiled resolver strategy instances per request.

---

## 2. Confirmed Integration Points

1. **Factory Compiler Entry Point**: In `ValueResolver.compile_resolver_config()`, add:
   ```python
   if kind == "collection":
       return CollectionResolver(
           source=config.get("source"),
           operation=config.get("operation", "any"),
           condition=config.get("condition"),
           target_field=config.get("target_field"),
       )
   ```
2. **Execution Context Delegation**: `CollectionResolver.resolve(context)` calls `get_context_value(context, self.source)` to resolve the array, and calls `self._compiled_evaluator.evaluate(doc, row=r)` to test row conditions.
3. **Caching**: Reuses `get_compiled_resolver(action, key, payload)` with zero changes required to the caching layer.

---

## 3. Proposed Collection Contract

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

## 4. Final Beta Operation Set

The Beta operation set is classified into **Core Backend Operations**, **UI Semantic Aliases**, and **Derived Operations**:

- **Core Backend Operations**:
  1. `count`: Count total or matching rows (`integer`).
  2. `any`: Short-circuiting boolean check (`boolean`).
  3. `all`: Short-circuiting boolean check (`boolean`).
  4. `first`: Retrieve top row or first row matching condition (`dict | None`).
  5. `filter`: Extract array of matching row dicts (`list[dict]`).
  6. `pluck`: Extract array of target field values (`list[Any]`).
- **UI Semantic Aliases**:
  7. `find`: Semantic UI alias for `first` with a required condition. Backend maps `find` directly to `first`.
- **Derived Operations**:
  8. `unique`: Derived from `pluck` with order-preserving distinct key extraction (`list[Any]`).

---

## 5. Explicitly Deferred Operations

- `last`: Deferred to avoid confusion between tail access and reverse predicate search.
- `map` / `transform`: Deferred (requires dedicated row expression engine).
- `sort` / `reverse`: Deferred (child table index `idx` order suffices for Beta).
- `groupby` / `partition`: Deferred due to high complexity.
- Direct Resolver Composition (`SUM(FILTER(...))`): Deferred (filtered sums must use Loop Action or intermediate variable assignment).
- Nested Collections (`doc.items[0].taxes`): Deferred.

---

## 6. Collection vs Loop Boundary

- **Loop Action (`Loop`)**: Imperative graph process control handler. Manages iteration state (`_loops`), executes child graph nodes, performs document mutations or external API calls per row.
- **Collection Resolver (`collection`)**: Pure, side-effect-free Value Resolver strategy. Computes inline values or filtered arrays synchronously inside expressions or assignments.

---

## 7. Collection vs Child Aggregation Boundary

- **Child Aggregation Resolver (`child_aggregation`)**: Unfiltered numeric reduction across all rows in a column (`sum`, `avg`, `count`).
- **Collection Resolver (`collection`)**: Filtered collection querying (`count` with condition, `filter`), boolean predicate checks (`any`, `all`), row lookups (`first`, `find`), and column extraction (`pluck`, `unique`).

---

## 8. Result-Type Compatibility

Verified in `assignment.py:119` and `ContextManager` that setting variable paths (`vars.filtered_items`) or document fields supports `list[dict]`, `dict`, `list[Any]`, `int`, `bool`, and `None` without requiring any changes to the result-handling framework.

---

## 9. Condition / Row-Context Compatibility

`ConditionEvaluator` natively supports row context via `evaluate(doc, row=r)`.
Scope prefixes:
- `row.<field>`: Resolves against current collection row.
- `doc.<field>`: Resolves against root document.
- `old_doc.<field>`: Resolves against pre-save document.
- `vars.<var>`: Resolves against execution context variables.

---

## 10. Source-Path Rules

Supported source patterns in Beta:
1. `doc.<child_table_fieldname>` (e.g. `doc.items`)
2. `vars.<variable_name>` (e.g. `vars.tax_list`)
3. `old_doc.<child_table_fieldname>` (e.g. `old_doc.items`)

Arbitrary nested paths (`doc.items[0].taxes`) or row scope sources (`row.items`) are rejected during validation in Beta.

---

## 11. Error and Empty-Value Semantics

| Input State | `count` | `any` | `all` | `first` / `find` | `filter` | `pluck` | `unique` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Empty collection `[]`** | `0` | `False` | `True` (vacuous) | `None` | `[]` | `[]` | `[]` |
| **`source = None`** | `0` | `False` | `False` | `None` | `[]` | `[]` | `[]` |
| **`source = non-list`** | `0` | `False` | `False` | `None` | `[]` | `[]` | `[]` |
| **Missing `target_field`** | N/A | N/A | N/A | N/A | N/A | `[]` | `[]` |

---

## 12. Security Model

- **Non-Eval Execution**: All predicates use structured JSON conditions evaluated by `ConditionEvaluator` using Python's `operator` module.
- **Controlled Exception Guard**: If a collection exceeds 10,000 rows (`MAX_COLLECTION_ROWS`), `CollectionResolver` raises a controlled `MethodExecutionError` rather than silently truncating user data.

---

## 13. Performance Model

- Algorithmic bounds:
  - `count`, `first`, `filter`, `pluck`, `unique`: O(N).
  - `any`: O(N) with O(1) early exit on first `True`.
  - `all`: O(N) with O(1) early exit on first `False`.
- Compiled evaluator instances are reused across all row iterations without JSON re-parsing.

---

## 14. Required Tests

Unit test suite `TestCollectionResolver` in `flexirule/ruleflow/tests/test_value_resolvers_complex.py` covering:
- All 8 operations/aliases.
- Empty collection, `None` collection, and non-list source handling.
- Row context isolation (`row.qty` vs `doc.qty`).
- 10,000 row iteration exception guard.
- Coexistence with `ChildAggregationResolver` and `LoopHandler`.

---

## 15. Open Questions

- **None**: All architectural integration contracts have been verified against actual repository source code.

---

## 16. Exact Implementation Scope

1. **`flexirule/ruleflow/core/value_resolver.py`**:
   - Add `CollectionResolver(CompiledResolver)` class.
   - Register `kind == "collection"` in `ValueResolver.compile_resolver_config()`.
2. **`flexirule/ruleflow/tests/test_value_resolvers_complex.py`**:
   - Add `TestCollectionResolver` test class.
3. **`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/CollectionResolver.vue`**:
   - Add frontend Vue component reusing `ComboBoxControl` and `SelectControl`.
4. **`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`**:
   - Register strategy `"collection"`.
5. **`flexirule/public/js/flexirule/core/formula_registry.js`**:
   - Register slash commands and update `getAllowedBuilderKinds()`.

---

## Final Decision

```
READY FOR IMPLEMENTATION
```
