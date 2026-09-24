# Canonical Resolver Contract Specification

## 1. Specification Overview

This document specifies the canonical JSON payload structure for FlexiRule's Value Resolvers in v1.0.

The canonical model replaces flat, implementation-centric `kind` values with a structured **`family + operation + config`** schema.

---

## 2. Canonical Payload Schema

Every canonical Value Resolver configuration persisted in rule nodes, actions, or sub-rule parameters MUST conform to the following JSON structure:

```json
{
  "family": "<string: family_name>",
  "operation": "<string: operation_name>",
  "config": {
    "<key>": "<value>"
  }
}
```

### Schema Definitions

1. **`family`** (Required, String):
   The top-level value domain. Must be one of:
   `"date"`, `"text"`, `"number"`, `"collection"`, `"lookup"`, `"system"`, `"conversion"`, `"conditional"`.

2. **`operation`** (Required, String):
   The specific operation name registered under the family (e.g. `"normalize"`, `"calculate"`, `"format_money"`, `"filter"`, `"pluck"`).

3. **`config`** (Required, Object):
   An operation-specific dictionary containing inputs, field references, parameters, and flags required to execute the operation.

---

## 3. Concrete Family & Operation Payload Examples

### 3.1 Text Family — Normalize Operation
```json
{
  "family": "text",
  "operation": "normalize",
  "config": {
    "source_type": "field",
    "source_field": "doc.item_name",
    "pipeline": ["trim", "slug", "lower"]
  }
}
```

### 3.2 Number Family — Format Money Operation
```json
{
  "family": "number",
  "operation": "format_money",
  "config": {
    "value_type": "field",
    "value_field": "doc.grand_total",
    "currency_type": "constant",
    "currency_constant": "USD",
    "decimals": 2
  }
}
```

### 3.3 Date Family — Calculate Date Operation
```json
{
  "family": "date",
  "operation": "calculate",
  "config": {
    "base_date_type": "field",
    "base_date_field": "doc.transaction_date",
    "operator": "add",
    "amount_type": "constant",
    "amount_value": 30,
    "unit": "days"
  }
}
```

### 3.4 Collection Family — Filter Operation
```json
{
  "family": "collection",
  "operation": "filter",
  "config": {
    "source": "doc.items",
    "condition": {
      "field": "row.rate",
      "operator": ">",
      "value": 100
    }
  }
}
```

### 3.5 Lookup Family — Get Field Operation
```json
{
  "family": "lookup",
  "operation": "field",
  "config": {
    "link_field": "doc.customer",
    "target_doctype": "Customer",
    "target_field": "customer_group"
  }
}
```

---

## 4. Normalization Layer & Legacy Payload Coexistence

To ensure 100% backward compatibility with development-era fixtures and test suites that use the legacy `{ "kind": "..." }` structure, a automatic normalizer function is embedded at the backend compiler boundary:

```python
def normalize_resolver_payload(payload: dict) -> dict:
    """Normalizes legacy { 'kind': '...' } payloads to canonical family + operation + config."""
    if not isinstance(payload, dict):
        return payload

    # Already canonical format
    if "family" in payload and "operation" in payload:
        return payload

    kind = payload.get("kind")
    if not kind:
        return payload

    # Legacy mapping dispatch
    legacy_map = {
        "date_formula": ("date", "calculate"),
        "date_diff": ("date", "diff"),
        "math_formula": ("number", "calculate"),
        "string_formula": ("text", "combine" if payload.get("str_op") == "concat" else "case"),
        "normalization": ("text", "normalize"),
        "format": ("number" if payload.get("fmt_op") == "fmt_money" else "text", "format_money" if payload.get("fmt_op") == "fmt_money" else "format"),
        "fetch": ("lookup", "field"),
        "system_context": ("system", payload.get("context_key", "user")),
        "collection": ("collection", payload.get("op", "filter")),
        "child_aggregation": ("collection", payload.get("agg_op", "sum"))
    }

    if kind in legacy_map:
        family, operation = legacy_map[kind]
        return {
            "family": family,
            "operation": operation,
            "config": payload
        }

    return payload
```

This normalization layer guarantees that any legacy test case or JSON fixture executes without error while emitting standard canonical contracts on write.
