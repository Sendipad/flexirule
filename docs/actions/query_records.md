---
title: "Query Records"
weight: 80
---

# Query Records Action

The **Query Records** action retrieves data from any DocType in the system.

## Query Modes

- **Query List**: Returns a list of records matching the filters.
- **Query Doc**: Returns a single record by name or ID.
- **Exist Record**: Returns `True` or `False` based on whether matching records exist.
- **Aggregate Operations**: `Count`, `Sum`, `Average`, `Min`, `Max`.
- **Group By**: Returns aggregated results grouped by a specific field.

## Filters

The visual filter builder allows you to define complex query criteria. You can use literal values or dynamic references from the context (e.g., {% raw %}`{{ doc.customer }}`{% endraw %}).

## Results

The result of a query can be stored in a **Context Variable** for use in subsequent actions, such as a **Loop** or **Assignment**.
