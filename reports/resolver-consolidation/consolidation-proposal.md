# Consolidation Proposal

## Target 9-Family Taxonomy

The consolidated FlexiRule Value Resolver architecture establishes 9 canonical domain-focused resolver families:

```text
Value Resolvers
├── 1. Value Source (`kind: "value_source"`)
├── 2. Date (`kind: "date"`)
├── 3. Text (`kind: "text"`)
├── 4. Math (`kind: "math"`)
├── 5. Collection (`kind: "collection"`)
├── 6. Aggregate (`kind: "aggregate"`)
├── 7. Lookup (`kind: "lookup"`)
├── 8. Conditional (`kind: "conditional"`)
└── 9. Type Conversion (`kind: "type_conversion"`)
```

---

## Detailed Specifications per Family

### 1. Value Source (`value_source`)
* **Operations**: `static`, `field`, `old_field`, `variable`, `system_context`
* **Schema**:
  ```json
  {
    "kind": "value_source",
    "operation": "field",
    "path": "doc.grand_total",
    "sys_token": "user",
    "sys_role": "Accounts Manager"
  }
  ```

### 2. Date (`date`)
* **Operations**: `add`, `subtract`, `diff`
* **Schema**:
  ```json
  {
    "kind": "date",
    "operation": "add",
    "base_type": "today",
    "base_field": "doc.posting_date",
    "offset_value": 7,
    "offset_unit": "days",
    "diff_start_field": "doc.start_date",
    "diff_end_field": "doc.end_date",
    "diff_unit": "days"
  }
  ```

### 3. Text (`text`)
* **Operations**: `concat`, `trim`, `lower`, `upper`, `replace`, `slug`, `snake`, `title`, `format_date`, `fmt_money`, `pattern`
* **Schema**:
  ```json
  {
    "kind": "text",
    "operation": "fmt_money",
    "field_a": "doc.grand_total",
    "field_b": "doc.currency",
    "pattern": "{0} - USD",
    "date_format": "YYYY-MM-DD"
  }
  ```

### 4. Math (`math`)
* **Operations**: `add` (`+`), `subtract` (`-`), `multiply` (`*`), `divide` (`/`), `min`, `max`, `round`
* **Schema**:
  ```json
  {
    "kind": "math",
    "operation": "+",
    "field_a": "doc.net_total",
    "field_b_type": "constant",
    "constant_b": 100,
    "precision": 2
  }
  ```

### 5. Collection (`collection`)
* **Operations**: `count`, `any`, `all`, `first`, `filter`, `pluck`, `unique`
* **Schema**:
  ```json
  {
    "kind": "collection",
    "source": "doc.items",
    "operation": "filter",
    "condition": [{"field": "qty", "operator": ">", "value": 10}],
    "target_field": "item_code"
  }
  ```

### 6. Aggregate (`aggregate`)
* **Operations**: `sum`, `avg`, `min`, `max`, `count`
* **Schema**:
  ```json
  {
    "kind": "aggregate",
    "agg_table": "doc.items",
    "agg_field": "amount",
    "agg_op": "sum"
  }
  ```

### 7. Lookup (`lookup`)
* **Operations**: `get`, `exists`
* **Schema**:
  ```json
  {
    "kind": "lookup",
    "operation": "get",
    "link_field": "doc.customer",
    "linked_doctype": "Customer",
    "fetch_field": "customer_group"
  }
  ```

### 8. Conditional (`conditional`)
* **Operations**: `if_then_else`
* **Schema**:
  ```json
  {
    "kind": "conditional",
    "condition": [{"field": "doc.status", "operator": "==", "value": "Approved"}],
    "true_value": "Active",
    "false_value": "Pending"
  }
  ```

### 9. Type Conversion (`type_conversion`)
* **Operations**: `text`, `integer`, `decimal`, `boolean`, `date`, `datetime`
* **Schema**:
  ```json
  {
    "kind": "type_conversion",
    "operation": "decimal",
    "field": "vars.raw_rate"
  }
  ```
