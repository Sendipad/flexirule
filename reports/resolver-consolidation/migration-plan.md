# Migration Plan

## Strategy Overview
The resolver consolidation uses **Non-Destructive Runtime Normalization**. Instead of executing risky SQL database migrations across all stored rules, normalization is performed on-the-fly during compilation in the backend and during component mount/deserialization in the frontend.

---

## Migration Flow

```text
Database (Saved Rule Payload)
          ↓
  [Backend Engine]                [Frontend UI Editor]
ValueResolver.compile_resolver_config()  useValueResolver.js (syncFromProps)
          ↓                                 ↓
Legacy Kind Detection            Legacy Kind Detection
          ↓                                 ↓
Normalize Payload to Canonical   Normalize Local State to Canonical
          ↓                                 ↓
Instantiate Canonical Resolver    Render Canonical Strategy UI Component
```

---

## Frontend Migration Steps
1. **Strategy Registry Updating**: Replace individual `DateFormulaResolver.vue`, `DateDiffResolver.vue`, `StringFormulaResolver.vue`, `NormalizationResolver.vue`, `FormatResolver.vue`, `AggregationResolver.vue`, `FetchResolver.vue`, `SystemContextResolver.vue` registrations in `strategies.js` with the 9 canonical strategy definitions (`value_source`, `date`, `text`, `math`, `collection`, `aggregate`, `lookup`, `conditional`, `type_conversion`).
2. **Deserialization Normalizer**: In `useValueResolver.js`, add `normalizeResolverPayload()`:
   * Maps `date_formula` and `date_diff` → `date`
   * Maps `string_formula`, `normalization`, `format` → `text`
   * Maps `math_formula` → `math`
   * Maps `child_aggregation` → `aggregate`
   * Maps `fetch` → `lookup`
   * Maps `system_context` → `value_source`

## Backend Migration Steps
1. **Refactor `value_resolver.py`**:
   * Implement canonical classes: `ValueSourceResolver`, `DateResolver`, `TextResolver`, `MathResolver`, `CollectionResolver`, `AggregateResolver`, `LookupResolver`, `ConditionalResolver`, `TypeConversionResolver`.
   * Update `ValueResolver.compile_resolver_config(config)` to inspect `kind` and route legacy `kind` payloads through canonical resolver constructors.
