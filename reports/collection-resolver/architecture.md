# Collection Resolver: System Architecture

## 1. Verified Core Architecture

The Collection Resolver integrates directly into FlexiRule's existing compiled resolver architecture.

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
        │  get_context_value  │               │ ConditionEvaluator  │
        │ (Collection Source) │               │   (Row Context)     │
        └─────────────────────┘               └─────────────────────┘
```

## 2. Verified Against Existing Source

### 2.1 Compiler Integration (`flexirule/ruleflow/core/value_resolver.py`)
- **Implementation Location**: `flexirule/ruleflow/core/value_resolver.py:465`
- **Verified Signature**:
  ```python
  @staticmethod
  def compile_resolver_config(config: dict) -> CompiledResolver:
  ```
- **Integration**:
  When `config.get("kind") == "collection"`, `compile_resolver_config` instantiates `CollectionResolver`:
  ```python
  if kind == "collection":
      return CollectionResolver(
          source=config.get("source"),
          operation=config.get("operation", "any"),
          condition=config.get("condition"),
          target_field=config.get("target_field"),
      )
  ```

### 2.2 Base Class Contract (`CompiledResolver`)
- **Implementation Location**: `flexirule/ruleflow/core/value_resolver.py:73`
- **Verified Signature**:
  ```python
  class CompiledResolver:
      def resolve(self, context: dict) -> Any:
          raise NotImplementedError()
  ```
- **Integration**: `CollectionResolver` subclasses `CompiledResolver` and implements `resolve(self, context: dict) -> Any`.

### 2.3 Context Value Resolution (`get_context_value`)
- **Implementation Location**: `flexirule/ruleflow/core/value_resolver.py:12`
- **Verified Signature**:
  ```python
  def get_context_value(context: dict, path: str | None) -> Any:
  ```
- **Behavior**: Traverses `doc`, `vars`, `item`, `loop`, `row`, or fallback root keys.
- **Integration**: Used by `CollectionResolver` to fetch the source array: `rows = get_context_value(context, self.source)`.

### 2.4 Row Predicate Evaluation (`ConditionEvaluator`)
- **Implementation Location**: `flexirule/ruleflow/core/evaluator.py:15`
- **Verified Signature**:
  ```python
  class ConditionEvaluator:
      def __init__(self, conditions_json: str):
      def evaluate(self, doc, row=None) -> bool:
  ```
- **Behavior**: Accepts a JSON array string of conditions. Evaluates left/right expressions against `doc` and `row` using safe built-in operators.
- **Integration**: `CollectionResolver` compiles its condition JSON in `__init__` once and reuses `self._compiled_evaluator.evaluate(doc, row=r)` across all collection items.

### 2.5 Request-Local Caching (`get_compiled_resolver`)
- **Implementation Location**: `flexirule/ruleflow/core/value_resolver.py:556`
- **Verified Signature**:
  ```python
  def get_compiled_resolver(action, key: str, value_payload: Any) -> CompiledResolver:
  ```
- **Behavior**: Caches compiled resolvers in `frappe.local.flexirule_compiled_resolvers` under key `{action_name}_{key}`. Fully compatible out of the box.

---

## 3. Result Contract & Consumer Verification
- **Verified Result Types**: `AssignmentHandler` (`assignment.py:119`), `ContextManager` (`context_manager.py`), and `QueryRecordsHandler` process resolver results. When target path is in `vars` (e.g. `vars.filtered_items`), `context["vars"]` is a standard dictionary accepting `list[dict]`, `dict`, `list[Any]`, `int`, `bool`, or `None`.
- **No Schema Modifications Required**: Resolvers are already allowed to return non-scalar structures (such as arrays and dictionaries).
