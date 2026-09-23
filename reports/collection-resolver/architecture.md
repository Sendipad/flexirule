# Collection Resolver: System Architecture

## 1. Architectural Philosophy
FlexiRule employs a multi-tiered execution architecture where dynamic data derivation is cleanly separated from graph execution and control flow.

Value Resolution is performed by compiled `CompiledResolver` strategy instances. These instances are generated during rule compilation / execution and evaluated against execution context.

```
                    ┌──────────────────────────────────┐
                    │       Rule Engine / Action       │
                    └─────────────────┬────────────────┘
                                      │
                         ValueResolver.compile()
                                      │
                                      ▼
               ┌─────────────────────────────────────────────┐
               │         CollectionResolver Strategy         │
               │            (CompiledResolver)               │
               └──────────────────────┬──────────────────────┘
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
        ┌─────────────────────┐               ┌─────────────────────┐
        │    FieldResolver    │               │ ConditionEvaluator  │
        │ (Collection Source) │               │   (Row Context)     │
        └─────────────────────┘               └─────────────────────┘
```

## 2. Integration Points

### 2.1 Compiler Integration (`flexirule/ruleflow/core/value_resolver.py`)
`ValueResolver.compile_resolver_config(config)` inspects the `kind` property of a resolver configuration dictionary.
When `kind == "collection"`, `ValueResolver` instantiates `CollectionResolver` with pre-validated parameters:
- `source`: Field path string pointing to collection (e.g. `doc.items`).
- `operation`: String key identifying operation (`any`, `all`, `count`, `first`, `last`, `find`, `filter`, `pluck`, `unique`).
- `condition`: Structured condition JSON or `None`.
- `target_field`: Target row field name (for `pluck` and `unique`).

### 2.2 Execution Context Architecture
The execution context passed into `CollectionResolver.resolve(context)` follows the standard FlexiRule structure:
```python
context = {
    "doc": <Frappe Document / Dict>,
    "vars": <Variable Dictionary>,
    "item": <Current Loop Item if applicable>,
    "row": <Current Row Dict during Collection iteration>
}
```

When evaluating conditions on individual rows during collection iteration, `CollectionResolver` constructs a lightweight local context frame or passes `doc` and `row` directly to `ConditionEvaluator.evaluate(doc, row=r)`.

### 2.3 Condition Evaluator Compatibility
FlexiRule's `ConditionEvaluator` already accepts `row` as a second parameter in `evaluate(doc, row=None)`.
Inside `_resolve_value(value_def, doc, row=None)`, when `ref` begins with `row.` or when `row` is provided, `ConditionEvaluator` resolves field values directly against the row object:
```python
if scope == "row" and row:
    return self._get_field_value(row, subpath)
```
This existing capability allows `CollectionResolver` to seamlessly evaluate complex row predicates without modifying `ConditionEvaluator`.

## 3. Core Design Principles
1. **Zero Production Code Intrusion During Design**: Design strictly integrates with current structures.
2. **Single Responsibility**: `CollectionResolver` only derives values from existing collections in context; it never mutates documents or executes side-effect actions.
3. **No Arbitrary Code Execution**: All row predicates use structured JSON conditions evaluated by `ConditionEvaluator`. Python `eval` / `exec` / `lambda` are forbidden.
4. **Backward Compatibility**: Existing rules with static values, formulas, or child aggregations remain 100% unaffected.
