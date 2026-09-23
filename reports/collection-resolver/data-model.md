# Collection Resolver: Data Model & Contracts

## 1. JSON Schema Contract

The Collection Resolver conforms to FlexiRule's `mode: "resolver"` JSON contract schema.

### 1.1 Complete Config Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CollectionResolverConfig",
  "type": "object",
  "required": ["kind", "operation", "source"],
  "properties": {
    "kind": {
      "type": "string",
      "const": "collection"
    },
    "operation": {
      "type": "string",
      "enum": ["count", "any", "all", "first", "last", "find", "filter", "pluck", "unique"]
    },
    "source": {
      "type": "string",
      "description": "Path to collection array in context (e.g. 'doc.items', 'vars.tax_list')"
    },
    "condition": {
      "type": "object",
      "description": "Structured condition JSON evaluated per row via ConditionEvaluator"
    },
    "target_field": {
      "type": ["string", "null"],
      "description": "Target field name on row dict (required for pluck and unique operations)"
    }
  }
}
```

---

## 2. Concrete Data Payload Examples

### Example 1: `ANY` Condition Check
Check if any row in `doc.items` has `qty > 100`:
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
    }
  }
}
```

### Example 2: `PLUCK` Field Values
Extract all `item_code` values from `doc.items`:
```json
{
  "mode": "resolver",
  "config": {
    "kind": "collection",
    "operation": "pluck",
    "source": "doc.items",
    "target_field": "item_code"
  }
}
```

### Example 3: `FILTER` Sub-Collection
Filter `doc.items` where `item_group == "Services"`:
```json
{
  "mode": "resolver",
  "config": {
    "kind": "collection",
    "operation": "filter",
    "source": "doc.items",
    "condition": {
      "left": { "ref": "row.item_group" },
      "op": "==",
      "right": { "value": "Services" }
    }
  }
}
```

### Example 4: Filtered `COUNT`
Count items in `doc.items` where `rate <= 0`:
```json
{
  "mode": "resolver",
  "config": {
    "kind": "collection",
    "operation": "count",
    "source": "doc.items",
    "condition": {
      "left": { "ref": "row.rate" },
      "op": "<=",
      "right": { "value": 0 }
    }
  }
}
```

---

## 3. Deserialization & Reconstruction Principles
The frontend control reconstructs its visual state deterministically from the `config` object:
1. `source` populates the child table / collection dropdown.
2. `operation` sets the operation dropdown (`any`, `pluck`, etc.).
3. `target_field` renders when `operation` is `pluck` or `unique`.
4. `condition` renders the filter row / predicate controls when `operation` accepts a condition.
