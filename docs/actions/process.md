---
title: "Process"
weight: 70
---

# Process Action

The **Process** action is the primary way to extend FlexiRule with custom Python code. It executes reusable business logic defined in a `Process` DocType.

## Key Features

- **Reusability**: Define logic once in a Process module and use it across multiple rules.
- **Configurable**: Uses JSON Schemas to generate a custom configuration UI in the Rule Builder.
- **Side-Effect Free**: Following the **Mutation Intent Architecture**, Processes should return data rather than directly modifying the database.

## Configuration

- **Process**: Select the target Process DocType.
- **Operation**: Choose the specific function within that Process to execute.
- **Config**: Provide inputs as defined by the operation's `config_schema`.

## Mutation Mode

After the Process executes, the Rule Engine applies the result based on the selected **Mutation Mode**:

- `Set Context Variable`: Stores the result in the `vars` dictionary.
- `Set Doc Field`: Updates a field on the primary document.
- `Update Doc Field`: Merges a dictionary result into the document's fields.
- `Batch Database Set`: Directly updates the database for performance (bypasses ORM).

## Standards

For detailed guidelines on creating custom Process adapters, see the [Process Adapter Standards](./standards.md).
