# Collection Resolver: Operation Analysis

This document provides a detailed specification for all candidate operations evaluated for the FlexiRule Collection Resolver Beta release.

---

## Candidate Operations Overview

| Operation | Input | Output | Result Type | Beta? | Primary Reason |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`count`** | Collection (+ Condition) | Item count | `integer` | **Yes** | High demand; simple O(N) evaluation. |
| **`any`** | Collection + Condition | Truth value | `boolean` | **Yes** | Essential predicate; short-circuits on `True`. |
| **`all`** | Collection + Condition | Truth value | `boolean` | **Yes** | Essential predicate; short-circuits on `False`. |
| **`first`** | Collection (+ Condition) | Matching row | `dict \| None` | **Yes** | Safe positional/predicate access. |
| **`last`** | Collection | Tail row | `dict \| None` | **Yes** | Safe O(1) tail element access. |
| **`find`** | Collection + Condition | Matching row | `dict \| None` | **Yes** | Clear semantic alias for `first(where)`. |
| **`filter`** | Collection + Condition | Sub-collection | `list[dict]` | **Yes** | Enables declarative sub-list derivation. |
| **`pluck`** | Collection + Field | Field values | `list[Any]` | **Yes** | Extracts specific column values into list. |
| **`unique`** | Collection + Field | Unique values | `list[Any]` | **Yes** | Extracts distinct column values into list. |
| *`map`* | Collection + Expression | Transformed list | `list[Any]` | **No** | Deferred: Requires row expression engine. |
| *`sort`* | Collection + Key | Sorted list | `list[dict]` | **No** | Deferred: Child table order (`idx`) suffices. |
| *`groupby`*| Collection + Key | Grouped dict | `dict[str, list]`| **No**| Deferred: High complexity for Beta. |

---

## Detailed Specifications for Beta Operations

### 1. `count`
- **Purpose**: Returns the number of rows in a collection, optionally filtered by a condition.
- **Input**:
  - `source`: Field path pointing to array (e.g. `doc.items`).
  - `condition` (optional): Structured condition JSON.
- **Output**: Integer count of total or matching items.
- **Edge Cases**: Empty collection returns `0`. Non-list source returns `0`.
- **Complexity**: O(N) where N is collection length.

### 2. `any`
- **Purpose**: Determines if at least one item in the collection satisfies the given condition.
- **Input**: `source`, `condition` (required).
- **Output**: `True` if any row matches; `False` otherwise.
- **Performance Optimization**: Short-circuits immediately upon encountering the first matching item (`True`).
- **Edge Cases**: Empty collection returns `False`.

### 3. `all`
- **Purpose**: Determines if every item in the collection satisfies the given condition.
- **Input**: `source`, `condition` (required).
- **Output**: `True` if all rows match; `False` otherwise.
- **Performance Optimization**: Short-circuits immediately upon encountering the first non-matching item (`False`).
- **Edge Cases**: Empty collection returns `True` (vacuous truth in boolean logic).

### 4. `first`
- **Purpose**: Returns the first item in the collection, or the first item matching an optional condition.
- **Input**: `source`, `condition` (optional).
- **Output**: Row dictionary object, or `None` if no match exists or collection is empty.
- **Edge Cases**: Empty collection returns `None`.

### 5. `last`
- **Purpose**: Returns the last item in the collection.
- **Input**: `source`.
- **Output**: Row dictionary object, or `None` if collection is empty.
- **Complexity**: O(1) via direct negative indexing (`items[-1]`).

### 6. `find`
- **Purpose**: Explicit search operation for the first row matching a required condition.
- **Input**: `source`, `condition` (required).
- **Output**: Row dictionary object, or `None` if no row matches.
- **Notes**: Behaves identically to `first` with a condition, but provides clear visual intent in the UI.

### 7. `filter`
- **Purpose**: Returns a new list containing only the row dictionaries that satisfy the condition.
- **Input**: `source`, `condition` (required).
- **Output**: `list[dict]` of matching rows.
- **Edge Cases**: If no items match, returns empty list `[]`.

### 8. `pluck`
- **Purpose**: Extracts a list of specific field values from every row in the collection.
- **Input**: `source`, `target_field` (string name of field, e.g. `item_code`).
- **Output**: `list[Any]` containing extracted field values (including `None` if missing).
- **Example**: `PLUCK(doc.items, "item_code")` -> `["ITEM-001", "ITEM-002"]`.

### 9. `unique`
- **Purpose**: Extracts a list of distinct, non-duplicate field values from rows in the collection.
- **Input**: `source`, `target_field`.
- **Output**: `list[Any]` containing unique values while preserving original order of appearance.
- **Implementation Note**: Uses order-preserving set deduplication:
  ```python
  seen = set()
  result = []
  for val in values:
      if val not in seen:
          seen.add(val)
          result.append(val)
  ```
