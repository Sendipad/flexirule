# Collection Resolver: Operation Analysis & Classification

## 1. Verified Classification Matrix

Following source verification, candidate operations are classified as Core Backend Operations, UI Convenience Aliases, Derived Operations, or Explicitly Deferred.

| Operation | Input | Output | Classification | Primary Reason |
| :--- | :--- | :--- | :--- | :--- |
| **`count`** | Source (+ Condition) | `integer` | **Core Backend** | Essential filterable counting; O(N). |
| **`any`** | Source + Condition | `boolean` | **Core Backend** | Essential predicate; short-circuits on `True`. |
| **`all`** | Source + Condition | `boolean` | **Core Backend** | Essential predicate; short-circuits on `False`. |
| **`first`** | Source (+ Condition) | `dict \| null` | **Core Backend** | Positional or predicate row lookup. |
| **`filter`** | Source + Condition | `list[dict]` | **Core Backend** | Extracts sub-collection array of matching row dicts. |
| **`pluck`** | Source + Field | `list[Any]` | **Core Backend** | Extracts array of field values from rows. |
| **`find`** | Source + Condition | `dict \| null` | **UI Alias** | Maps directly to `first` on the backend. |
| **`unique`** | Source + Field | `list[Any]` | **Derived** | Derived from `pluck` with order-preserving distinct key lookup. |
| *`last`* | Source | `dict \| null` | **Deferred** | Deferred to keep search directions unconfused in Beta. |
| *`map`* | Source + Expr | `list[Any]` | **Deferred** | Requires row expression engine. |
| *`sort`* | Source + Key | `list[dict]` | **Deferred** | Child table index `idx` order suffices for Beta. |
| *`groupby`*| Source + Key | `dict` | **Deferred** | High complexity. |

---

## 2. Verified Operational Specifications for Beta

### 2.1 `count`
- **Behavior**: Returns the count of items in `source`. If `condition` is present, counts only rows matching `condition`.
- **Empty / Null Input**: `0`.

### 2.2 `any`
- **Behavior**: Returns `True` if at least one row matches `condition`. Short-circuits immediately on first `True`.
- **Empty / Null Input**: `False`.

### 2.3 `all`
- **Behavior**: Returns `True` if all rows match `condition`. Short-circuits immediately on first `False`.
- **Empty / Null Input**: `True` if `source` is a valid empty list `[]` (vacuous truth); `False` if `source` is `None` or invalid.

### 2.4 `first` (and `find` alias)
- **Behavior**: Returns the first row dict matching `condition` (or top element if no condition). Returns `None` if no match exists.
- **Empty / Null Input**: `None`.

### 2.5 `filter`
- **Behavior**: Returns a `list[dict]` containing all row dictionaries that satisfy `condition`.
- **Empty / Null Input**: `[]`.

### 2.6 `pluck`
- **Behavior**: Extracts a `list[Any]` containing `target_field` values from matching rows.
- **Empty / Null Input**: `[]`.

### 2.7 `unique`
- **Behavior**: Extracts a `list[Any]` containing distinct `target_field` values from matching rows while preserving insertion order.
- **First Occurrence Included, Duplicates Filtered**: When extracting `target_field` values across collection rows, the first occurrence of `None` (or an empty string `""` or `0`) in a matching row will be preserved in the returned result array. Subsequent rows with the same `None` or empty value are recognized as duplicates and skipped.
- **`None` vs Empty String (`""`) Distinction**: `None` (missing/null field) and `""` (empty string) are distinct values in Python and set tracking. If a collection contains rows with both `None` and `""`, the result array will contain one `None` and one `""` (e.g., `["Hardware", None, "Software", ""]`).
- **Complex / Dictionary Row Values**: If the target field value is a nested dictionary or list, it is canonicalized (via sorted JSON serialization) so that structurally identical objects are properly de-duplicated.
- **All Missing / Empty Collection**: If no rows match the filter condition or if `target_field` is not specified, `unique` returns an empty list `[]`.

#### Example:
```python
rows = [
    {"item_code": "ITEM-A", "group": "Hardware"},
    {"item_code": "ITEM-B", "group": None},
    {"item_code": "ITEM-C", "group": "Hardware"},
    {"item_code": "ITEM-D", "group": None},
    {"item_code": "ITEM-E", "group": ""},
]

# CollectionResolver(source="doc.items", operation="unique", target_field="group")
# Result: ["Hardware", None, ""]
```
