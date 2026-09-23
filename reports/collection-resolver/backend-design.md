# Collection Resolver: Backend Design & Implementation

## 1. Class Architecture (`flexirule/ruleflow/core/value_resolver.py`)

The backend implementation introduces `CollectionResolver` inheriting from `CompiledResolver`.

```python
class CollectionResolver(CompiledResolver):
    """
    Compiled resolver strategy for querying, checking, filtering, and extracting
    values from child table collections or list variables.
    """
    def __init__(
        self,
        source: str | None,
        operation: str = "any",
        condition: dict | None = None,
        target_field: str | None = None,
    ):
        self.source = source
        self.operation = (operation or "any").lower()
        self.condition = condition
        self.target_field = target_field
        self._compiled_evaluator = None

        if self.condition:
            from flexirule.ruleflow.core.evaluator import ConditionEvaluator
            import json
            cond_json = json.dumps([self.condition]) if isinstance(self.condition, dict) else json.dumps(self.condition)
            self._compiled_evaluator = ConditionEvaluator(cond_json)

    def resolve(self, context: dict) -> Any:
        rows = get_context_value(context, self.source)
        if not rows or not isinstance(rows, list):
            if self.operation in ("count",):
                return 0
            if self.operation in ("filter", "pluck", "unique"):
                return []
            if self.operation == "all":
                return True
            return None

        # Maximum safety iteration guard
        MAX_ROWS = 10000
        bounded_rows = rows[:MAX_ROWS]

        doc = context.get("doc")

        def _matches(row) -> bool:
            if not self._compiled_evaluator:
                return True
            return self._compiled_evaluator.evaluate(doc, row=row)

        op = self.operation

        if op == "count":
            if not self._compiled_evaluator:
                return len(bounded_rows)
            return sum(1 for r in bounded_rows if _matches(r))

        if op == "any":
            if not self._compiled_evaluator:
                return len(bounded_rows) > 0
            return any(_matches(r) for r in bounded_rows)

        if op == "all":
            if not self._compiled_evaluator:
                return True
            return all(_matches(r) for r in bounded_rows)

        if op in ("first", "find"):
            for r in bounded_rows:
                if _matches(r):
                    return r
            return None

        if op == "last":
            for r in reversed(bounded_rows):
                if _matches(r):
                    return r
            return None

        if op == "filter":
            return [r for r in bounded_rows if _matches(r)]

        if op == "pluck":
            if not self.target_field:
                return []
            return [
                r.get(self.target_field) if isinstance(r, dict) or hasattr(r, "get") else None
                for r in bounded_rows
                if _matches(r)
            ]

        if op == "unique":
            if not self.target_field:
                return []
            seen = set()
            res = []
            for r in bounded_rows:
                if _matches(r):
                    val = r.get(self.target_field) if isinstance(r, dict) or hasattr(r, "get") else None
                    if val not in seen:
                        seen.add(val)
                        res.append(val)
            return res

        return None
```

---

## 2. Factory Compiler Registration (`ValueResolver.compile_resolver_config`)

In `ValueResolver.compile_resolver_config(config)`:

```python
if kind == "collection":
    return CollectionResolver(
        source=config.get("source"),
        operation=config.get("operation", "any"),
        condition=config.get("condition"),
        target_field=config.get("target_field"),
    )
```

---

## 3. Evaluation Context Handling
- `get_context_value(context, self.source)` resolves the target collection array (e.g., `doc.items` or `vars.tax_list`).
- Each item in the collection array is passed as `row` to `ConditionEvaluator.evaluate(doc, row=row)`.
- If a row field is referenced (e.g. `row.qty`), `ConditionEvaluator` resolves `row.qty` from the `row` dict directly.
