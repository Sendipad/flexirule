# Condition System<no value>

# Condition System Architecture

FlexiRule employs a sophisticated, high-performance condition system that allows users to build complex logic visually while executing it with the speed and safety of native Python.

## Ubiquitous Usage

The Condition Builder is not limited to a single "Condition" node; it is a pervasive component used throughout FlexiRule to drive logic-based execution at multiple levels:

- **Rule Trigger Eligibility**: Every Rule has a global condition defined at the DocType level. This is evaluated by the `RuleCoordinator` to decide if a rule should skip or start execution.
- **Node-Level Branching**: The `Condition` action node uses it to split the execution path into True/False branches.
- **Row-Level Assignment (`Run If`)**: In `Assignment` actions, each mutation can have its own "Run If" condition, allowing for granular, state-dependent updates within a single batch.
- **Collection Filtering**: Used within `Loop` and `Collection` nodes to filter datasets or define exit criteria.
- **Switch Case Logic**: The `Switch` action uses multiple condition blocks to determine which path to follow among many options.

## The Three-Tier Architecture

The system is divided into three distinct layers, ensuring a clean separation between user interface, logic representation, and execution.

### 1. The Visual Builder (Frontend)

The **Condition Builder** is a recursive Vue 3 interface that allows users to construct logic trees.

- **Input**: User interactions (drag-and-drop, field selection, operator picking).
- **Output**: A standardized **JSON AST (Abstract Syntax Tree)**.
- **Key Files**: `ConditionBuilder.vue`, `ConditionNode.vue`, `SimpleCondition.vue`.
- **Detailed Guide**: [Condition Builder Frontend](../builder/condition_builder.md)

### 2. The Condition Compiler (Backend - Save-Time)

To avoid the overhead of parsing JSON at runtime, FlexiRule uses a "Save-Time Compilation" strategy. When a Rule is saved, the `ConditionCompiler` processes the JSON AST.

- **Input**: JSON AST.
- **Output**: An optimized **Python Expression String** and a list of **Watched Fields**.
- **Optimization**: The compiler translates visual groups into native Python `and`/`or` chains and collections into efficient generator expressions (e.g., `any(row.status == 'Open' for row in doc.items)`).
- **Key Files**: `compiler.py`.

### 3. The Evaluator (Backend - Runtime)

At runtime, the execution engine evaluates the pre-compiled Python string within a sandboxed environment.

- **Input**: Compiled Python string + Execution Context (`doc`, `vars`, etc.).
- **Execution**: Uses `frappe.safe_eval` for maximum performance with guaranteed security.
- **Security**: Restricted to `SafeFrappeAPI`, preventing any write operations or unauthorized access during evaluation.
- **Key Files**: `runtime_eval.py`, `engine.py`.

## The Condition Evaluator (`ConditionEvaluator`)

While the compiler is the modern preferred path, FlexiRule maintains a `ConditionEvaluator` class that can interpret the JSON AST directly. This is primarily used for:

1. **Legacy Compatibility**: Rules created before the pre-compiler was introduced.
2. **Immediate Feedback**: Running "Live Tests" or "Simulations" in the builder without requiring a database save.

### Evaluation Lifecycle

1. **Context Resolution**: The evaluator resolves values from the `doc` or `row` objects based on the node's `ref` path.
2. **Recursive Traversal**: The evaluator walks the JSON tree, applying the logical operators (`AND`/`OR`) and quantifiers (`ANY`/`ALL`).
3. **Coercion**: Values are automatically coerced (e.g., `1` for True, `0` for False) to ensure consistency with Frappe's field values.

---

## The Condition Compiler (`ConditionCompiler`)

The `ConditionCompiler` is responsible for transforming the structured JSON representation of conditions into a valid, safe, and optimized Python expression.

### 1. JSON Schema (AST)

The compiler expects three types of nodes:

- **Condition Node**: A leaf node representing a single comparison.
    ```json
    { "left": { "ref": "doc.status" }, "op": "==", "right": { "value": "Open" } }
    ```
- **Group Node**: A logical container for multiple nodes.
    ```json
    { "op": "and", "conditions": [...] }
    ```
- **Collection Node**: Logic applied across a child table or list.
    ```json
    { "op": "any", "collection": "doc.items", "alias": "item", "where": { ... } }
    ```

### 2. Operator Translation

The compiler maps visual operators to Python equivalents and helper functions:

| Visual Operator      | Python/Helper Expression                             |
| :------------------- | :--------------------------------------------------- |
| `==`, `!=`, `>`, `<` | Native Python operators                              |
| `is_set`             | `(lhs is not None and lhs != '')`                    |
| `is_empty`           | `is_empty_value(lhs)`                                |
| `contains`           | `(rhs in str(lhs) if lhs else False)`                |
| `length_gt`          | `(length_of(lhs) > rhs)`                             |
| `in`                 | `check_link_match(lhs, rhs, 'in')` (for Link fields) |

### 3. Collection Logic (any/all/none)

One of the most powerful features of the compiler is how it handles child tables using Python generator expressions:

- **Any**: `any(condition for alias in (collection or []))`
- **All**: `all(condition for alias in (collection or []))`
- **None**: `not any(condition for alias in (collection or []))`

Example: "Check if any item has a quantity greater than 10" becomes:
`any(item.get('qty') > 10 for item in (doc.get('items') or []))`

### 4. Scope Resolution

The compiler intelligently resolves variable scopes:

- `doc.status` -> `doc.get('status')`
- `row.price` -> `row.get('price')`
- Deep paths like `doc.owner.email` are wrapped in a `resolve()` helper: `resolve(doc, 'owner.email')`.

## Performance: Why Pre-Compilation?

Traditional no-code engines often interpret JSON logic trees at runtime. This involves recursive function calls and dictionary lookups for every single comparison, which is slow.

FlexiRule's approach provides several advantages:

1.  **Fast Evaluation**: Compiled Python strings run at near-native speeds.
2.  **Short-Circuiting**: We leverage Python's native `and`/`or` short-circuiting. If the first part of an `AND` is false, the rest isn't even evaluated.
3.  **Static Analysis (Watched Fields)**: By compiling at save-time, we can use regex to extract which fields the condition depends on. This allows the `RuleCoordinator` to skip rule execution entirely if none of the "Watched Fields" have changed, drastically reducing CPU load.
4.  **Dry-Run Validation**: We can validate the syntax and safety of the generated Python code before the rule is even activated.
