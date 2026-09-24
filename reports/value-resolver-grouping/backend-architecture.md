# Backend Architecture & Execution Specifications

## 1. Backend Resolver Architecture

The backend Value Resolver system in `flexirule/ruleflow/core/value_resolver.py` is structured into three primary layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      ValueResolver Factory & API                       │
│              ValueResolver.compile_resolver_config(config)             │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
    Canonical Family Dispatch                Legacy Normalization Dispatch
   (family + operation + config)                 ({ "kind": "..." })
               │                                       │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
                    CompiledResolver Strategy Instances
   ┌──────────────────────────────────────────────────────────────────┐
   │ DateFormulaResolver | DateDiffResolver | MathFormulaResolver     │
   │ NormalizationResolver | StringFormulaResolver | FormatResolver    │
   │ CollectionResolver | ChildAggregationResolver | FetchResolver    │
   └──────────────────────────────────────────────────────────────────┘
```

---

## 2. Dispatch & Normalization Pipeline

When `ValueResolver.compile_resolver_config(config)` is invoked:

1. **Format Detection**:
   The input dictionary is inspected. If it contains `family` and `operation`, it is routed through `_compile_canonical_family()`. Otherwise, it passes through `_normalize_legacy_payload()` before compilation.

2. **Canonical Family Dispatcher**:
   ```python
   CANONICAL_FAMILY_MAP = {
       "date": {
           "calculate": DateFormulaResolver,
           "diff": DateDiffResolver,
           "format": FormatResolver
       },
       "text": {
           "combine": StringFormulaResolver,
           "case": NormalizationResolver,
           "normalize": NormalizationResolver,
           "format": FormatResolver
       },
       "number": {
           "calculate": MathFormulaResolver,
           "round": MathFormulaResolver,
           "format_money": FormatResolver,
           "percentage": MathFormulaResolver
       },
       "collection": {
           "count": CollectionResolver,
           "any": CollectionResolver,
           "all": CollectionResolver,
           "first": CollectionResolver,
           "find": CollectionResolver,
           "filter": CollectionResolver,
           "pluck": CollectionResolver,
           "unique": CollectionResolver,
           "sum": ChildAggregationResolver,
           "average": ChildAggregationResolver
       },
       "lookup": {
           "field": FetchResolver,
           "record": FetchResolver
       },
       "system": {
           "user": SystemContextResolver,
           "roles": SystemContextResolver,
           "today": SystemContextResolver,
           "now": SystemContextResolver,
           "company": SystemContextResolver
       }
   }
   ```

3. **Compiler Instantiation**:
   The mapped strategy class is instantiated with the operation config and returns a `CompiledResolver` instance ready for AST code generation or evaluation.

---

## 3. Execution Strategies & AST Generation

Each `CompiledResolver` strategy provides two resolution modes:

### Mode 1: AST Code Generation (`to_python_expr()`)
Returns a safe Python string expression for direct inclusion in compiled rule functions:
- `DateFormulaResolver` → `"frappe.utils.add_to_date(doc.transaction_date, days=30)"`
- `NormalizationResolver` → `"execute_normalization_pipeline(doc.title, ['trim', 'slug'])"`
- `FormatResolver` (`format_money`) → `"frappe.utils.fmt_money(doc.grand_total, currency='USD')"`

### Mode 2: Direct Evaluation (`resolve(context)`)
Executes the resolver directly against a runtime `RuleContext` dictionary:
- Intercepts field lookups via `FieldResolver`.
- Evaluates predicate conditions in collections using `ConditionEvaluator`.
- Applies memory-safe bounds (e.g. `MAX_COLLECTION_ROWS = 10000`).
