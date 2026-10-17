# Canonical Resolver Contract & Explicit Legacy Adapter Specification

## 1. Canonical Schema Definition

The canonical payload structure for Value Resolvers in FlexiRule v1.0 uses a structured **`family + operation + config`** JSON schema.

```json
{
  "family": "<string: family_name>",
  "operation": "<string: operation_name>",
  "config": {
    "<key>": "<value>"
  }
}
```

---

## 2. Explicit Legacy Adapters (Field-Level Mapping)

To prevent nesting old schema structures inside the new schema (i.e. avoiding `"config": { "kind": "...", ... }`), every development-era legacy payload is converted to canonical format through an **explicit field-level legacy adapter**.

---

### Adapter 1: `date_formula` Adapter
```python
# Input Legacy Payload
{"kind": "date_formula", "base_type": "field", "base_field": "doc.date", "offset_value": 5, "offset_unit": "days", "offset_sign": "+"}

# Adapter Mapping
canonical_family = "date"
canonical_operation = "calculate"
canonical_config = {
    "base_date_type": legacy.get("base_type", "field"),
    "base_date_field": legacy.get("base_field"),
    "amount_value": legacy.get("offset_value", 0),
    "amount_unit": legacy.get("offset_unit", "days"),
    "operator": "add" if legacy.get("offset_sign") == "+" else "subtract"
}
```

---

### Adapter 2: `normalization` Adapter
```python
# Input Legacy Payload
{"kind": "normalization", "norm_field": "doc.title", "norm_pipeline": ["trim", "slug"]}

# Adapter Mapping
canonical_family = "text"
canonical_operation = "normalize"
canonical_config = {
    "source_field": legacy.get("norm_field"),
    "pipeline": legacy.get("norm_pipeline", [])
}
```

---

### Adapter 3: `format` (`fmt_money`) Adapter
```python
# Input Legacy Payload
{"kind": "format", "fmt_op": "fmt_money", "fmt_field": "doc.grand_total", "fmt_config": "USD"}

# Adapter Mapping
canonical_family = "number"
canonical_operation = "format_money"
canonical_config = {
    "source_field": legacy.get("fmt_field"),
    "currency": legacy.get("fmt_config", "USD")
}
```

---

### Adapter 4: `string_formula` Adapter
```python
# Input Legacy Payload (Concat)
{"kind": "string_formula", "str_op": "concat", "str_a": "doc.first_name", "str_b": "doc.last_name"}

# Adapter Mapping
canonical_family = "text"
canonical_operation = "combine"
canonical_config = {
    "items": [legacy.get("str_a"), legacy.get("str_b")],
    "delimiter": " "
}
```

---

### Adapter 5: `child_aggregation` Adapter
```python
# Input Legacy Payload
{"kind": "child_aggregation", "agg_table": "doc.items", "agg_field": "amount", "agg_op": "sum"}

# Adapter Mapping
canonical_family = "collection"
canonical_operation = legacy.get("agg_op") if legacy.get("agg_op") in ("sum", "count") else "average"
canonical_config = {
    "source": legacy.get("agg_table"),
    "target_field": legacy.get("agg_field")
}
```

---

### Adapter 6: `fetch` Adapter
```python
# Input Legacy Payload
{"kind": "fetch", "link_field": "doc.customer", "fetch_field": "customer_group", "linked_doctype": "Customer"}

# Adapter Mapping
canonical_family = "lookup"
canonical_operation = "field"
canonical_config = {
    "link_field": legacy.get("link_field"),
    "target_field": legacy.get("fetch_field"),
    "target_doctype": legacy.get("linked_doctype")
}
```

---

## 3. Strict Failure on Unknown Legacy Payload

If an incoming legacy payload contains an unmapped or unrecognized `kind` or `str_op`/`fmt_op`, the normalizer **MUST NOT** silently guess or reinterpret the payload. It raises an explicit exception:

```python
class UnrecognizedResolverPayloadError(ValueError):
    """Raised when an incoming legacy payload cannot be deterministically mapped."""
    pass
```
