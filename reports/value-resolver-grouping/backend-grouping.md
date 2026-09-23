# Backend Resolver Architecture Grouping Analysis

## Executive Summary

This report analyzes how the Python backend architecture in FlexiRule handles Value Resolver compilation, dispatching, and execution, and evaluates how a 3-tier hierarchy (**Resolver -> Family -> Operation -> Executor**) can be implemented cleanly without breaking backwards compatibility.

---

## 1. Current Backend Dispatch Architecture

Currently, `flexirule/ruleflow/core/value_resolver.py` implements a flat dispatcher structure:

```python
class ValueResolver:
    @staticmethod
    def compile_resolver_config(config: dict) -> CompiledResolver:
        kind = config.get("kind")

        if kind == "date_formula":
            return DateFormulaResolver(...)
        if kind == "math_formula":
            return MathFormulaResolver(...)
        if kind == "date_diff":
            return DateDiffResolver(...)
        if kind == "child_aggregation":
            return ChildAggregationResolver(...)
        if kind == "string_formula":
            return StringFormulaResolver(...)
        if kind == "normalization":
            return NormalizationResolver(...)
        if kind == "format":
            return FormatResolver(...)
        if kind == "fetch":
            return FetchResolver(...)
        if kind == "system_context":
            return SystemContextResolver(...)
        if kind == "collection":
            return CollectionResolver(...)

        return NoneResolver()
```

### Observations:
1. `compile_resolver_config` uses a flat `if/elif` chain checking the `kind` property.
2. Each resolver kind corresponds directly to a dedicated `CompiledResolver` subclass (`DateFormulaResolver`, `CollectionResolver`, etc.).
3. `CollectionResolver` is unique among resolvers because it already implements internal operation dispatching based on `config.get("operation")` (`count`, `any`, `all`, `first`, `filter`, `pluck`, `unique`).

---

## 2. Proposed Backend Hierarchical Architecture

A maintainable backend design introduces family registry classes or family dispatchers:

```
+-----------------------------------------------------------------------------------+
|                               ValueResolver.compile                               |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                             Resolver Family Registry                              |
+-----------------------------------------------------------------------------------+
       |                            |                           |
       v                            v                           v
+---------------+          +-------------------+       +------------------+
| Transform     |          | Collection        |       | Retrieval        |
| Family        |          | Family            |       | Family           |
+---------------+          +-------------------+       +------------------+
       |                            |                           |
       v                            v                           v
+---------------+          +-------------------+       +------------------+
| Math / Date / |          | Filter / Pluck /  |       | Fetch / Context /|
| String / Norm |          | Sum / Avg / Count |       | Variable         |
+---------------+          +-------------------+       +------------------+
```

### Conceptual Code Refactoring Pattern (Zero-Breakage):

```python
class ResolverFamily:
    """Base class for family executors."""
    @classmethod
    def compile(cls, config: dict) -> CompiledResolver:
        raise NotImplementedError()

class TransformFamily(ResolverFamily):
    @classmethod
    def compile(cls, config: dict) -> CompiledResolver:
        op = config.get("operation") or config.get("kind")
        if op in ("math_formula", "math"):
            return MathFormulaResolver(...)
        if op in ("date_formula", "date"):
            return DateFormulaResolver(...)
        ...

# Main Dispatcher remains backwards-compatible with legacy 'kind'
RESOLVER_FAMILY_MAP = {
    "transform": TransformFamily,
    "math_formula": TransformFamily,
    "date_formula": TransformFamily,
    "collection": CollectionFamily,
    "child_aggregation": CollectionFamily,
    "fetch": RetrievalFamily,
    "system_context": SystemContextFamily,
}
```

---

## 3. Advantages of Backend Grouping

1. **Pluggable Registration**: Resolvers can be registered via Python decorators or entrypoints rather than modifying a monolithic `if/elif` block.
2. **Shared Validation**: Family-level validation rules (such as validating field references or context paths) can be inherited from `ResolverFamily` base class.
3. **Optimized Request-Local Caching**: `get_compiled_resolver` in `value_resolver.py` continues caching compiled instances efficiently per action key.
