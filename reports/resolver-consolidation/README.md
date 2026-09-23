# FlexiRule Resolver Consolidation, Deduplication & Operation Unification Report

## Executive Summary

This directory contains the definitive architectural audit and implementation plan for consolidating, deduplicating, and unifying **Value Resolvers and Resolver Operations** in FlexiRule (Frappe v15+).

FlexiRule previously exposed 10 independent UI resolver kinds and multiple execution mechanisms. This consolidation establishes a small, coherent, extensible **9-family taxonomy** anchored on user-facing domain semantics rather than internal technical execution strategies.

---

## Navigation & Sub-Reports

| Sub-Report | Description |
| :--- | :--- |
| **[1. Resolver Inventory](resolver-inventory.md)** | Definitive inventory table mapping all frontend and backend resolvers, inputs, outputs, and overlap flags. |
| **[2. Operation Inventory](operation-inventory.md)** | Operation-by-operation breakdown across all resolvers identifying duplicate or mergeable operations. |
| **[3. Duplication Analysis](duplication-analysis.md)** | Deep conceptual analysis comparing Date, Text, Math, Collection, Lookup, Value Sources, and Execution Strategies. |
| **[4. Consolidation Proposal](consolidation-proposal.md)** | Specification of the target 9-family taxonomy (`value_source`, `date`, `text`, `math`, `collection`, `aggregate`, `lookup`, `conditional`, `type_conversion`). |
| **[5. Compatibility Analysis](compatibility-analysis.md)** | In-depth evaluation of legacy saved configurations (`date_formula`, `date_diff`, `child_aggregation`, `string_formula`, `normalization`, `format`, `fetch`, `system_context`) and runtime aliasing. |
| **[6. Migration Plan](migration-plan.md)** | Technical strategy for zero-downtime runtime normalization and UI deserialization without destructive DB migrations. |
| **[7. Test Plan](test-plan.md)** | Matrix of unit, integration, and UI test cases covering canonical resolvers, legacy compatibility, edge cases, and security boundaries. |
| **[8. Implementation Report](implementation-report.md)** | Final code-level summary of changes across frontend, backend, contracts, and test suite. |

---

## Answers to Core Consolidation Questions

### 1. Which resolvers are duplicates or overlapping?
* **Date**: `date_formula` and `date_diff` overlapped in date manipulation/arithmetic responsibilities.
* **Text**: `string_formula`, `normalization`, and `format` all performed string transformation, formatting, and casing.
* **Math & Aggregation**: `math_formula` handled binary arithmetic, while `child_aggregation` duplicated aggregate functions (`sum`, `avg`, `count`) over child tables.
* **Lookup**: `fetch` was a single-purpose link field getter; `Collection` performed array search/filter (`first`, `find`).
* **Value Source & Context**: `system_context` (user/role) was isolated from standard document field (`doc.`) and variable (`vars.`) lookups.

### 2. Which operations are duplicates?
* `string_formula.uppercase` vs `normalization.upper` (Upper case).
* `string_formula.lowercase` vs `normalization.lower` (Lower case).
* `string_formula.fmt_money` vs `format.fmt_money` (Money formatting).
* `child_aggregation.count` vs `collection.count` (Count operations).
* `collection.find` vs `collection.first` (First matching element).

### 3. Which resolvers are merged?
* `date_formula` + `date_diff` → **`date`** resolver (operations: `add`, `subtract`, `diff`).
* `string_formula` + `normalization` + `format` → **`text`** resolver (operations: `concat`, `trim`, `lower`, `upper`, `replace`, `slug`, `snake`, `title`, `format_date`, `fmt_money`, `pattern`).
* `math_formula` → **`math`** resolver (operations: `+`, `-`, `*`, `/`, `min`, `max`, `round`).
* `child_aggregation` → Split into **`aggregate`** (for scalar reductions: `sum`, `avg`, `min`, `max`, `count`) and **`collection`** (for list operations).
* `fetch` → **`lookup`** resolver (operations: `get`, `exists`).
* `system_context` + variable/field references → **`value_source`** resolver (operations: `static`, `field`, `old_field`, `variable`, `system_context`).

### 4. Which resolvers remain separate?
* **`collection`** vs **`aggregate`**: `collection` returns lists or booleans or single row objects (`filter`, `pluck`, `unique`, `any`, `all`, `first`), whereas `aggregate` reduces a collection down to a single numeric scalar (`sum`, `avg`, `min`, `max`, `count`).
* **`lookup`** vs **`collection`**: `lookup` queries the Frappe database (`frappe.db.get_value` / DB queries), whereas `collection` operates in-memory on context arrays/child tables (`doc.items`).

### 5. What are the new canonical resolver types?
1. `value_source`
2. `date`
3. `text`
4. `math`
5. `collection`
6. `aggregate`
7. `lookup`
8. `conditional`
9. `type_conversion`

### 6. What legacy aliases remain supported?
All legacy resolver kind strings (`date_formula`, `date_diff`, `math_formula`, `string_formula`, `normalization`, `format`, `fetch`, `system_context`, `child_aggregation`) are preserved in `ValueResolver.compile_resolver_config()` with automatic runtime translation to canonical compiled resolvers. Old saved rules execute without modification or error.

---

## Canonical Target Taxonomy Summary

```text
Value Resolvers (Canonical Taxonomy)
│
├── Value Source (`kind: "value_source"`)
│   ├── static
│   ├── field
│   ├── old_field
│   ├── variable
│   └── system_context
│
├── Date (`kind: "date"`)
│   ├── add
│   ├── subtract
│   └── diff
│
├── Text (`kind: "text"`)
│   ├── concat
│   ├── trim
│   ├── lower
│   ├── upper
│   ├── replace
│   ├── slug
│   ├── snake
│   ├── title
│   ├── format_date
│   ├── fmt_money
│   └── pattern
│
├── Math (`kind: "math"`)
│   ├── add (+)
│   ├── subtract (-)
│   ├── multiply (*)
│   ├── divide (/)
│   ├── min
│   ├── max
│   └── round
│
├── Collection (`kind: "collection"`)
│   ├── count
│   ├── any
│   ├── all
│   ├── first
│   ├── filter
│   ├── pluck
│   └── unique
│
├── Aggregate (`kind: "aggregate"`)
│   ├── sum
│   ├── avg
│   ├── min
│   ├── max
│   └── count
│
├── Lookup (`kind: "lookup"`)
│   ├── get
│   └── exists
│
├── Conditional (`kind: "conditional"`)
│   └── if_then_else
│
└── Type Conversion (`kind: "type_conversion"`)
    ├── text
    ├── integer
    ├── decimal
    ├── boolean
    ├── date
    └── datetime
```
