# Collection Resolver: Backend Design & Implementation

## 1. Verified Class Architecture (`flexirule/ruleflow/core/value_resolver.py`)

The backend implementation introduces `CollectionResolver` inheriting from `CompiledResolver`.

```python
import json
from typing import Any
import frappe
from frappe import _
from flexirule.ruleflow.core.exceptions import MethodExecutionError

class CollectionResolver(CompiledResolver):
    """
    Compiled resolver strategy for querying, checking, filtering, and extracting
    values from child table collections or list variables.
    """
    MAX_COLLECTION_ROWS = 10000

    def __init__(
        self,
        source: str | None,
        operation: str = "any",
        condition: dict | list | None = None,
        target_field: str | None = None,
    ):
        self.source = source
        self.operation = (operation or "any").lower()
        if self.operation == "find":
            self.operation = "first"  # Map UI alias directly
        self.condition = condition
        self.target_field = target_field
        self._compiled_evaluator = None

        if self.condition:
            from flexirule.ruleflow.core.evaluator import ConditionEvaluator
            cond_list = self.condition if isinstance(self.condition, list) else [self.condition]
            self._compiled_evaluator = ConditionEvaluator(json.dumps(cond_list))

    def resolve(self, context: dict) -> Any:
        rows = get_context_value(context, self.source)
        if rows is None or not isinstance(rows, list):
            if self.operation == "count":
                return 0
            if self.operation in ("filter", "pluck", "unique"):
                return []
            if self.operation == "all":
                return True if rows is not None and isinstance(rows, list) else False
            return None

        # Guard against huge collections to prevent silent corruption or memory exhaust
        if len(rows) > self.MAX_COLLECTION_ROWS:
            raise MethodExecutionError(
                _("Collection '{0}' exceeds maximum execution limit of {1} rows (got {2} rows).")
                .format(self.source, self.MAX_COLLECTION_ROWS, len(rows))
            )

        doc = context.get("doc")

        def _matches(r) -> bool:
            if not self._compiled_evaluator:
                return True
            return self._compiled_evaluator.evaluate(doc, row=r)

        op = self.operation

        if op == "count":
            if not self._compiled_evaluator:
                return len(rows)
            return sum(1 for r in rows if _matches(r))

        if op == "any":
            if not self._compiled_evaluator:
                return len(rows) > 0
            return any(_matches(r) for r in rows)

        if op == "all":
            if not self._compiled_evaluator:
                return True
            return all(_matches(r) for r in rows)

        if op == "first":
            for r in rows:
                if _matches(r):
                    return r
            return None

        if op == "filter":
            return [r for r in rows if _matches(r)]

        if op == "pluck":
            if not self.target_field:
                return []
            return [
                self._get_row_field(r, self.target_field)
                for r in rows
                if _matches(r)
            ]

        if op == "unique":
            if not self.target_field:
                return []
            seen = set()
            res = []
            for r in rows:
                if _matches(r):
                    val = self._get_row_field(r, self.target_field)
                    try:
                        key = val
                        if isinstance(val, (dict, list)):
                            key = json.dumps(val, sort_keys=True)
                    except Exception:
                        key = str(val)
                    if key not in seen:
                        seen.add(key)
                        res.append(val)
            return res

        return None

    @staticmethod
    def _get_row_field(row: Any, fieldname: str) -> Any:
        if row is None or not fieldname:
            return None
        if isinstance(row, dict) or hasattr(row, "get"):
            return row.get(fieldname)
        return getattr(row, fieldname, None)
```

---

## 2. Factory Compiler Registration (`ValueResolver.compile_resolver_config`)

In `ValueResolver.compile_resolver_config(config)` at `flexirule/ruleflow/core/value_resolver.py:465`:

```python
if kind == "collection":
    return CollectionResolver(
        source=config.get("source"),
        operation=config.get("operation", "any"),
        condition=config.get("condition"),
        target_field=config.get("target_field"),
    )
```
