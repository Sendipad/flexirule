# Backward Compatibility & Serialization Impact Analysis

## Executive Summary

This report evaluates the backward compatibility risks, serialization models, token representation impacts, and migration strategies involved in grouping FlexiRule Value Resolvers.

---

## 1. Token Serialization Model Analysis

In FlexiRule, `FlexValueControl.vue` and `serialization.js` manage resolver tokens within rich text fields using HTML `<span>` attributes and JSON payload coercion.

### Current Token Structure (HTML Span):
```html
<span data-token-type="resolver"
      data-expression="{frappe.utils.add_days(doc.posting_date, 7)}"
      data-label="Date: posting_date +7 days"
      data-config='{"kind":"date_formula","base_type":"doc_field","base_field":"posting_date","offset_sign":"+","offset_value":7,"offset_unit":"days"}'>
</span>
```

### Serialized JSON Payload (`coerceStructuredValue`):
```json
{
  "mode": "resolver",
  "value": "{frappe.utils.add_days(doc.posting_date, 7)}",
  "config": {
    "kind": "date_formula",
    "base_type": "doc_field",
    "base_field": "posting_date",
    "offset_sign": "+",
    "offset_value": 7,
    "offset_unit": "days"
  }
}
```

---

## 2. Token Evolution Models Comparison

### Model A: Flat Kind Expansion
- **Format**: `"kind": "collection_filter"`, `"kind": "collection_pluck"`
- **Assessment**: **REJECTED**. Creates hundreds of top-level kinds, breaks existing strategy registries, requires backend dispatcher rewrites, and fragments UI controls.

### Model B: Hierarchical Family + Operation (RECOMMENDED)
- **Format**: `"kind": "collection"`, `"operation": "filter"`
- **Assessment**: **APPROVED**. Already natively used by `CollectionResolver`. Extends cleanly to all resolver families without breaking existing token parsers.

---

## 3. Backward Compatibility Strategy (Zero-Breakage Legacy Mapping)

To ensure stored rules created with earlier versions of FlexiRule continue running flawlessly, the backend compiler and frontend deserializer must employ **In-Memory Aliasing**:

1. **Backend Legacy Dispatching**:
   In `ValueResolver.compile_resolver_config`, if a legacy `kind` (e.g. `"child_aggregation"`) is encountered, dynamically map it to the corresponding family and operation in memory without requiring database SQL migrations on stored Rule JSON.
2. **Frontend Deserialization Mapping**:
   In `FlexValueControl.vue:coerceStructuredValue`, legacy modes (`"formula"`, `"format"`, `"normalize"`) are already automatically coerced to `"mode": "resolver"`. This same mechanism transparently maps legacy config shapes upon UI load.

---

## 4. Master Compatibility & Migration Matrix

| Current Resolver Kind | Proposed Family | Proposed Operation | Backend Legacy Support | Migration Complexity | Compatibility Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `date_formula` | `transform` | `date_add` | In-memory alias `date_formula` -> `transform.date_add` | Low | None |
| `math_formula` | `transform` | `math` | In-memory alias `math_formula` -> `transform.math` | Low | None |
| `date_diff` | `transform` | `date_diff` | In-memory alias `date_diff` -> `transform.date_diff` | Low | None |
| `string_formula` | `transform` | `text_op` | In-memory alias `string_formula` -> `transform.text_op` | Low | None |
| `normalization` | `transform` | `normalize` | In-memory alias `normalization` -> `transform.normalize` | Low | None |
| `format` | `transform` | `format` | In-memory alias `format` -> `transform.format` | Low | None |
| `child_aggregation` | `collection` | `sum`/`avg`/`count` | Transparently route `child_aggregation` config to `CollectionResolver` | Medium | Low |
| `collection` | `collection` | `count`/`any`/`all`/`first`/`filter`/`pluck`/`unique` | Native match (No change required) | None | None |
| `fetch` | `retrieval` | `fetch` | In-memory alias `fetch` -> `retrieval.fetch` | Low | None |
| `system_context` | `retrieval` | `system_context` | In-memory alias `system_context` -> `retrieval.system_context` | Low | None |
