# Collection Resolver: Security & Performance Analysis

## 1. Security Architecture

### 1.1 Non-Eval Execution Paradigm
Collection Resolver strict design forbids standard Python string evaluation (`eval()`, `exec()`, `compile()`, `lambda`).
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
- Field access is restricted to dictionary `.get()` / attribute access on existing document/row dictionaries in context.
- No arbitrary attribute navigation (e.g. `__class__`, `__globals__`, `__subclasses__`) is permitted.
- `ConditionEvaluator` sanitizes field paths and restricts scope prefixes to `doc`, `row`, `old_doc`, and `vars`.

---

## 2. Performance Analysis & Safeguards

### 2.1 Complexity Analysis
- `last`: O(1) tail access.
- `count`, `first`, `find`, `any`, `all`, `filter`, `pluck`, `unique`: O(N) linear scan over collection size N.
- **Short-circuiting**:
  - `any`: Stops scanning on first `True` match (best case O(1), worst case O(N)).
  - `all`: Stops scanning on first `False` match (best case O(1), worst case O(N)).
  - `first` / `find`: Stops scanning on first match (best case O(1), worst case O(N)).

### 2.2 Collection Iteration Guard
To protect system memory and prevent CPU Denial of Service (DoS) from malicious or unexpectedly huge collections, `CollectionResolver` enforces a strict row limit:
```python
MAX_COLLECTION_ROWS = 10000
bounded_rows = rows[:MAX_COLLECTION_ROWS]
```
If a collection exceeds 10,000 items, `CollectionResolver` logs a system warning and safely processes the initial 10,000 rows.

### 2.3 Benchmarks Matrix (Expected Execution Time)
| Collection Size | Operation | Expected Time (ms) |
| :--- | :--- | :--- |
| **10 rows** | `any` / `count` / `filter` | < 0.1 ms |
| **100 rows** | `any` / `count` / `filter` | ~ 0.2 - 0.5 ms |
| **1,000 rows** | `filter` / `pluck` | ~ 2.0 - 4.0 ms |
| **10,000 rows** | `filter` (Max Guard) | ~ 20.0 - 35.0 ms |

---

## 3. Caching & Request-Local Optimization
`get_compiled_resolver(action, key, value_payload)` stores compiled `CollectionResolver` instances in `frappe.local.flexirule_compiled_resolvers`.
Condition JSON parsing and `ConditionEvaluator` instantiation occur **once** during compilation, ensuring zero JSON parsing overhead during repeated row iterations.
