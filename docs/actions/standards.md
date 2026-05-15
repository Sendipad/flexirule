# Process Adapter Standards

Processes are the primary extensibility point for FlexiRule. A **Process** is a grouping of **Operations** (Python functions) that can be called from the visual builder.

## Designing a Standard Process

### 1. Creation
Create a `Process` document in Frappe.
- Set a **Unique Name** (e.g., `Financial Utils`).
- Check **Is Standard** if you want Frappe to generate boilerplate code in your app.

### 2. Operations Child Table
Define each function in the Operations table:
- **Function Name**: The exact name of the Python function.
- **Icon/Color**: Visual cues for the builder.
- **Contract Settings**:
    - **Writes To**: `Document`, `Database`, `Context`, or `None`. This defines the *intent* of the operation.
    - **Requires Doc**: Does the function need a Frappe document to work?
    - **Transactional**: Should this operation be wrapped in a database savepoint?

### 3. Schemas (JSON)
Schemas define the UI for your operation.
- **Config Schema**: Defines the inputs (e.g., `limit`, `status`). Use standard JSON Schema with custom `ui_schema` extensions.
- **Output Schema**: Defines what the function returns. This allows the builder to provide autocomplete for the result.

---

## Coding Standards

### Controller Structure (`.py`)
Standard processes use a class-based structure:

```python
class MyProcess:
    def execute(self, context, func, config):
        # Dispatcher
        if hasattr(self, func):
            return getattr(self, func)(context, config)
        raise AttributeError(f"Operation {func} not found")

    def my_operation(self, context, config):
        doc = context.get('doc')
        limit = config.get('limit', 10)

        # Logic here
        # Processes should remain side-effect free (avoid direct doc.save() or frappe.db.set_value)
        result = do_calculation(doc, limit)

        # Return serializable data or mutation intents
        return result
```

### Best Practices
- **Mutation Intent Architecture**: Processes should not perform direct mutations on the database or the document. Instead, they should return data. The Rule Engine applies these changes based on the **Mutation Mode** configured by the rule designer in the builder.
- **Idempotency**: Operations should be designed so that re-executing them (on retry) is safe.
- **Context Awareness**: Use `context.get('vars')` to access intermediate data from previous steps.
- **Result Format**: Always return a serializable value (dict, list, int, str, bool).
- **Error Handling**: Raise `frappe.ValidationError` for business logic errors; the engine will handle logging and the `on_error` policy.

---

## Frontend Controllers (`.js`)
If your process requires custom UI components (e.g., a special map picker), you can define a `.js` file for your process.
- FlexiRule automatically loads these scripts when the process is selected in the builder.
- You can register custom control components to be used in the node configuration sidebar.
