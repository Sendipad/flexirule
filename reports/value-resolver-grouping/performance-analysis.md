# Performance Analysis & Bounds

## 1. Algorithmic Complexity & Micro-Benchmarks

The consolidated Value Resolver architecture was evaluated for computational efficiency across compilation, runtime resolution, memory overhead, and frontend rendering.

| Resolver Family | Operation | Time Complexity | Space Complexity | Performance Notes / Limits |
| :--- | :--- | :--- | :--- | :--- |
| **Date & Time** | `calculate` / `diff` | $O(1)$ | $O(1)$ | Native C-level `datetime` arithmetic via `frappe.utils`. |
| **Text** | `normalize` | $O(N)$ (string len) | $O(N)$ | Direct CPython string method execution. |
| **Number** | `calculate` | $O(1)$ | $O(1)$ | Fast compiled bytecode evaluation via `SafeEval`. |
| **Collections** | `count` / `any` / `all` | $O(N)$ ($N \le 10,000$) | $O(1)$ | Short-circuiting iteration; early return on match. |
| **Collections** | `filter` / `pluck` | $O(N)$ ($N \le 10,000$) | $O(N)$ | Enforces `MAX_COLLECTION_ROWS = 10,000` guard. |
| **Lookup** | `field` | $O(1)$ (cached) | $O(1)$ | Utilizes `frappe.cache` and request-local memory cache. |

---

## 2. Collection Execution Safety Guards

To prevent unbounded memory allocation or CPU starvation when processing large child tables in `CollectionResolver`:

```python
MAX_COLLECTION_ROWS = 10000

def resolve_collection(self, context):
    items = self._get_source_collection(context)
    if len(items) > MAX_COLLECTION_ROWS:
        raise MethodExecutionError(
            f"Collection size ({len(items)}) exceeds maximum safety threshold ({MAX_COLLECTION_ROWS})."
        )
```

---

## 3. Frontend Rendering Optimization

1. **Lazy Loading of Family Components**:
   Family components (`DateResolver.vue`, `TextResolver.vue`, etc.) are loaded asynchronously or via `markRaw()` in the family registry, avoiding bulk component tree overhead during visual canvas initial load.

2. **Reactivity Guarding**:
   State updates in `useValueResolver` during family or operation switching use `isInitializing` guards to prevent cascading Pinia store `mark_dirty()` triggers and $O(N^2)$ canvas re-renders.
