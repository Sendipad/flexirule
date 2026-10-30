# Collection Resolver vs Loop Action vs Child Aggregation

## 1. Verified Boundary Framework

FlexiRule maintains three distinct mechanisms for working with child tables. Each mechanism addresses a different functional layer:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FlexiRule Boundary Framework                          │
├──────────────────────────────┬──────────────────────────────┬───────────────┤
│         LOOP ACTION          │    COLLECTION RESOLVER       │   CHILD AGG   │
├──────────────────────────────┼──────────────────────────────┼───────────────┤
│ Category: Control Flow       │ Category: Value Resolver     │ Category: Val │
│ Purpose: Imperative Graph    │ Purpose: Declarative Query   │ Purpose: Math │
│ Side Effects: YES            │ Side Effects: NONE (Pure)    │ Side Effects: │
│ Context: Manages `_loops`    │ Context: Reads `row` context │ Context: Reads│
└──────────────────────────────┴──────────────────────────────┴───────────────┘
```

---

## 2. Canonical Mechanism Mapping

To avoid duplicate capabilities, FlexiRule assigns specific child-table requirements to canonical mechanisms:

| Specific Requirement | Canonical FlexiRule Mechanism | Architectural Reason |
| :--- | :--- | :--- |
| `COUNT(items)` | **Child Aggregation** or **Collection (`count`)** | Simple row count without filters. |
| `SUM(items.amount)` | **Child Aggregation** (`agg_op: "sum"`) | Unfiltered numeric column sum across all rows. |
| `COUNT(items WHERE qty > 0)` | **Collection Resolver** (`count`, condition) | Filtered row counting. |
| `SUM(items.amount WHERE qty > 0)` | **Loop Action + Variable** | Filtered sum requiring numeric reduction over filtered set. |
| `ANY(items WHERE qty > 100)` | **Collection Resolver** (`any`, condition) | Declarative boolean predicate check. |
| `FIRST(items WHERE qty > 100)` | **Collection Resolver** (`first`, condition) | Declarative row lookup. |
| `FILTER(items WHERE qty > 100)` | **Collection Resolver** (`filter`, condition) | Declarative sub-list extraction. |
| `PLUCK(items, "item_code")` | **Collection Resolver** (`pluck`) | Column value extraction. |

---

## 3. Resolver Composition Policy

**Explicit Non-Goal for Beta**: Direct nesting of resolvers (e.g. `SUM(FILTER(doc.items, qty > 100))` or `CHILD_AGGREGATION(COLLECTION_RESOLVER)`) is **explicitly deferred**.

Supporting arbitrary resolver composition introduces deep schema complexity and recursion risk. For Beta, filtered numeric reduction must be performed via a Loop Action or intermediate variable assignment.
