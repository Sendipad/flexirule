# <no value>
# Resolver: Resolver Engine

## 🎯 The Purpose of Resolvers

Resolvers are the "Data Glue" of FlexiRule. They solve a fundamental problem: **How do we get dynamic data into an action without writing Python?**

Instead of hardcoding field paths, FlexiRule uses a **Value Resolution Pipeline**.

---

## 🏗️ Resolver Architecture

The engine uses a **Compiled Resolver Graph**. When a rule is loaded, its dynamic values are "compiled" into optimized resolver objects.

### The `CompiledResolver` Hierarchy

- **`StaticResolver`**: Returns a constant value.
- **`VariableResolver`**: Resolves a path like `doc.customer_name` or `vars.total`.
- **`MathFormulaResolver`**: Performs arithmetic (`a + b`, `a * b`) on context variables.
- **`DateFormulaResolver`**: Handles date math (`Today + 7 days`).
- **`NormalizationResolver`**: Cleans data (Trimming, Scrubbing).
- **`FormatResolver`**: Formats dates and currency.
- **`ExpressionResolver`**: The most powerful—it chains multiple segments (Text + Token + Token) into a single result.

---

## 🔗 The Resolution Lifecycle

1. **Request**: An action needs a value (e.g., "Assign to Field").
2. **Dispatch**: The `ValueResolver.compile` method determines the resolver type from the configuration JSON.
3. **Execution**: The `resolve(context)` method is called. It performs the logic (e.g., fetching from DB, calculating a sum).
4. **Output**: The raw value is returned to the action.

---

## 💎 Hidden Power: Chained Composition

Because resolvers are objects, they can be nested.

- A `NormalizationResolver` can take the output of a `VariableResolver`.
- An `ExpressionResolver` can combine a `StaticResolver` ("Order #") with a `VariableResolver` (`doc.name`).

This enables **Low-Code Logic Composition**:

> "Format the (Sum of (Child Table.Amount)) as Currency (USD)"

---

## 🚀 Latent Capabilities

The architecture is prepared for even more advanced patterns:

- **Recursive Resolution**: Resolvers that resolve other resolvers.
- **Lazy Evaluation**: Values that are only calculated when actually accessed.
- **Caching**: The `get_compiled_resolver` helper already uses request-local caching, making the system extremely fast even with hundreds of dynamic bindings.
