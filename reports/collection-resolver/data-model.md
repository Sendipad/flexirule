# Collection Resolver: Data Model & Contracts

## 1. Verified JSON Schema Contract

The Collection Resolver JSON structure conforms to existing FlexiRule resolver schemas (e.g. `kind: "child_aggregation"`, `kind: "math_formula"`).

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
      "enum": ["count", "any", "all", "first", "find", "filter", "pluck", "unique"]
    },
    "source": {
      "type": "string",
      "description": "Path to collection in context: 'doc.<table_field>', 'vars.<var_name>', 'old_doc.<table_field>'"
    },
    "condition": {
      "type": "object",
      "description": "Structured condition payload evaluated per row via ConditionEvaluator"
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

### Example 1: `ANY` Predicate Check
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

---

## 3. Verified Source Path Rules

The `source` string must strictly match one of the following scope patterns:
1. `doc.<child_table_fieldname>` (e.g. `doc.items`)
2. `vars.<variable_name>` (e.g. `vars.tax_list`)
3. `old_doc.<child_table_fieldname>` (e.g. `old_doc.items`)

Arbitrary nested indexing (`doc.items[0].taxes`) or row scope sources (`row.items`) are rejected in Beta during validation.
