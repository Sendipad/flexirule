# Collection Resolver vs Loop Action vs Child Aggregation

## 1. Executive Problem Statement
To ensure a clean, unconfused engine architecture, FlexiRule must maintain strict boundaries between its three child-table manipulation mechanisms:
1. **Loop Action** (`Loop` handler)
2. **Child Aggregation Resolver** (`child_aggregation` strategy)
3. **Collection Resolver** (`collection` strategy)

Creating redundant or overlapping concepts causes user confusion, complicates UI design, and bloats backend code.

---

## 2. Definitive Responsibility Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FlexiRule Architecture                            │
├──────────────────────────────┬──────────────────────────────┬───────────────┤
│         LOOP ACTION          │    COLLECTION RESOLVER       │   CHILD AGG   │
├──────────────────────────────┼──────────────────────────────┼───────────────┤
│ Category: Control Flow       │ Category: Value Resolver     │ Category: Val │
│ Nature: Imperative Graph     │ Nature: Pure Declarative     │ Nature: Simple│
│ Side Effects: YES            │ Side Effects: NONE (Pure)    │ Side Effects: │
│ Context: Manages `_loops`    │ Context: Reads `row` context │ Context: Reads│
└──────────────────────────────┴──────────────────────────────┴───────────────┘
```

### 2.1 Loop Action (`Loop`)
- **Type**: Graph Execution Node (Control Flow Action).
- **Core Purpose**: Imperative multi-step iteration over a collection to execute child actions or graph branches.
- **When to Use**:
  - Updating fields on every child row or related documents.
  - Calling external APIs or triggering sub-rules per row.
  - Branching rule flow based on complex per-row state.
- **Example**:
  ```
  Loop through doc.items as item:
      If item.qty > 100:
          Document Action: Create Stock Requisition for item.item_code
  ```

### 2.2 Child Aggregation Resolver (`child_aggregation`)
- **Type**: Unfiltered Numeric Value Resolver.
- **Core Purpose**: Fast, lightweight mathematical reduction across all rows in a table field.
- **Supported Operations**: `sum`, `avg`, `count`.
- **When to Use**: Simple sum or average of a numeric column without row filters.
- **Example**: `SUM(doc.items.amount)` -> Sums `amount` across all rows in `doc.items`.

### 2.3 Collection Resolver (`collection`)
- **Type**: Filtered / Querying Value Resolver.
- **Core Purpose**: Declarative querying, predicate testing, filtering, or column extraction from collections inside expressions or field assignments.
- **Supported Operations**: `count` (with filter), `any`, `all`, `first`, `last`, `find`, `filter`, `pluck`, `unique`.
- **When to Use**:
  - Checking a condition across rows inline without adding a Loop node to the canvas.
  - Extracting a list of codes or filtered rows for assignment into a variable.
- **Example**: `ANY(doc.items where qty > 100)` -> Returns `True`/`False` inline.

---

## 3. Comparison & Overlap Matrix

| Capability | Loop Action | Child Aggregation | Collection Resolver | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **Row-by-Row Side Effects** | **YES** | NO | NO | Loop Action owns side effects exclusively. |
| **Graph Branching** | **YES** | NO | NO | Loop Action owns process graph flow. |
| **Unfiltered Column Sum** | Possible (verbose) | **YES** (Optimized) | Possible | Child Aggregation owns simple numeric sums. |
| **Filtered Row Count** | Verbose | NO | **YES** | Collection Resolver owns filtered counting. |
| **Inline Predicate Check** | Requires Loop + Var | NO | **YES** | Collection Resolver owns inline `ANY`/`ALL`. |
| **Extract Field List** | Requires Loop + Var | NO | **YES** | Collection Resolver owns `PLUCK`/`UNIQUE`. |

---

## 4. Architectural Reuse & Non-Duplication
To prevent duplicating execution logic:
1. **Reuse `ConditionEvaluator`**: Collection Resolver delegates row condition testing directly to `ConditionEvaluator.evaluate(doc, row=r)`.
2. **Reuse `FieldResolver`**: Collection Resolver resolves the source array using `FieldResolver.resolve(doc, "items")`.
3. **No Redundant Aggregators**: Simple `sum` and `avg` remain in `ChildAggregationResolver`. Filtered numeric aggregation can be achieved by passing a `filter` collection result into numeric helpers or composing resolvers.
