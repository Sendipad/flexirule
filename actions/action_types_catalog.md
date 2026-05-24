# Actions: Action Types Catalog

## 📚 Discovered Action Primitives
This catalog describes the building blocks of FlexiRule orchestration.

### 1. Assignment
- **Purpose**: Update fields or variables.
- **Runtime**: Performs sequential mutations on the `ExecutionContext`.
- **Flexibility**: Supports arithmetic, date math, and string concatenation via resolvers.
- **Enterprise Power**: Allows complex state transitions (e.g., "If Status is Open, set Assigned Date to Today").

### 2. Condition (Decision)
- **Purpose**: Binary branching (True/False).
- **Runtime**: Evaluates a compiled Python expression.
- **Flexibility**: Supports nested AND/OR logic and collection-based checks (any/all).

### 3. Switch
- **Purpose**: Multi-path branching based on conditions.
- **Runtime**: Evaluates cases in priority order and follows the first match.

### 4. Loop (Collection Iterator)
- **Purpose**: Execute a sub-graph for each item in a list.
- **Runtime**: Manages an internal iterator and injects the `item` into the context of its children.
- **Orchestration**: Essential for batch processing (e.g., "For each item in Sales Order, check stock").

### 5. Process
- **Purpose**: Execute a reusable, developer-defined operation.
- **Runtime**: Calls a specific Python method with contract-based validation.
- **Capability**: Can trigger side effects, return data, or request state mutations.

### 6. Query Records
- **Purpose**: Fetch data from other DocTypes.
- **Runtime**: Executes a filtered database lookup.
- **Flexibility**: Resolves filters dynamically from the current context.

### 7. Sub-Rule
- **Purpose**: Hierarchical orchestration.
- **Runtime**: Invokes another Rule engine instance and merges the resulting context.
- **Power**: Enables "SoC" (Separation of Concerns) in complex automation.

---

## 🏗️ Reusable Orchestration Patterns

### The "Enrichment" Pattern
1. **Query Records**: Fetch related Customer data.
2. **Assignment**: Populate current document fields from the queried record.

### The "Validation" Pattern
1. **Condition**: Check complex multi-field rules.
2. **Process (Stop)**: If invalid, call a process that throws a `frappe.ValidationError`.

### The "Transformation" Pipeline
1. **Loop**: Iterate over a collection.
2. **Assignment**: Use resolvers to transform data in each row.
3. **Process (External API)**: Send the cleaned collection to an external system.
