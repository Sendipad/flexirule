# Collection Resolver: Security & Performance Analysis

## 1. Security Architecture

### 1.1 Non-Eval Execution Paradigm
Collection Resolver's verified design forbids standard Python string evaluation (`eval()`, `exec()`, `compile()`, `lambda`).
All row predicate evaluation is delegated exclusively to `ConditionEvaluator`, which parses structured JSON condition nodes and maps comparison operators to safe Python `operator` module functions (`operator.eq`, `operator.gt`, `operator.lt`, etc.).

```
┌────────────────────────────────────────────────────────┐
│                   Structured JSON                      │
│ { "left": {"ref": "row.qty"}, "op": ">", "right": 100 } │
└───────────────────────────┬────────────────────────────┘
                            │
               No eval() / Safe Operator Call
                            │
                            ▼
                  operator.gt(row.qty, 100)
```

### 1.2 Access Control & Field Resolution
- Field access is restricted to dictionary `.get()` / attribute access on existing document/row dictionaries in context via `_get_row_field(row, fieldname)`.
- No arbitrary attribute navigation (e.g. `__class__`, `__globals__`, `__subclasses__`) is permitted.
- `ConditionEvaluator` sanitizes field paths and restricts scope prefixes to `doc`, `row`, `old_doc`, and `vars`.

---

## 2. Performance Analysis & Algorithmic Complexity

### 2.1 Algorithmic Complexity Bounds
- `count`, `first` (without condition), `filter`, `pluck`, `unique`: **O(N)** linear iteration over collection size N.
- `any`: **O(N)** linear iteration with best-case **O(1)** early short-circuiting on first `True` match.
- `all`: **O(N)** linear iteration with best-case **O(1)** early short-circuiting on first `False` match.

### 2.2 Collection Iteration Guard (Controlled Exception)
To prevent silent data corruption (e.g. returning a false count of `10,000` on a `15,000` row collection) and guard against CPU Denial of Service (DoS), `CollectionResolver` enforces a strict row limit:
```python
MAX_COLLECTION_ROWS = 10000
if len(rows) > MAX_COLLECTION_ROWS:
    raise MethodExecutionError(
        _("Collection '{0}' exceeds maximum execution limit of {1} rows.")
        .format(self.source, MAX_COLLECTION_ROWS)
    )
```
This guarantees rule execution fails visibly and predictably rather than returning factually incorrect truncated results.

---

## 3. Caching & Request-Local Optimization
`get_compiled_resolver(action, key, value_payload)` stores compiled `CollectionResolver` instances in `frappe.local.flexirule_compiled_resolvers`.
Condition JSON parsing and `ConditionEvaluator` instantiation occur **once** during compilation, ensuring zero JSON parsing overhead during repeated row iterations.
