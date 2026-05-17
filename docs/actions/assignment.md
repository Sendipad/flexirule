# Assignment Action

The **Assignment** action is a powerful tool for performing batch state mutations on the current document or context variables. It replaces the legacy **Set Value** action with a more robust system that supports multiple operators and sequential execution.

## Key Features

- **Batch Processing**: Define multiple mutations within a single action node.
- **Multiple Operators**: Beyond simple assignment, it supports math, list operations, and object merging.
- **Path Validation**: Prevents accidental mutation of protected system paths.

## Operators

The Assignment action utilizes a registry of operators, each designed for specific data types:

| Operator                       | Description                                                           | Supported Types | Idempotent |
| :----------------------------- | :-------------------------------------------------------------------- | :-------------- | :--------- |
| **Set Value** (`set`)          | Replaces the target with a new value.                                 | All             | Yes        |
| **Clear** (`clear`)            | Resets the target to its default empty state (null, empty list, etc). | All             | Yes        |
| **Increment By** (`increment`) | Adds a numeric value to the target.                                   | Numeric         | No         |
| **Decrement By** (`decrement`) | Subtracts a numeric value from the target.                            | Numeric         | No         |
| **Append To List** (`append`)  | Adds an item to the end of a list.                                    | Tables, Lists   | No         |
| **Merge Object** (`merge`)     | Merges a dictionary into the target object.                           | JSON, Dicts     | No         |
| **Toggle Boolean** (`toggle`)  | Flips a boolean value (1 to 0, 0 to 1).                               | Check           | No         |

## Target Paths

Assignments can target two primary scopes:

### 1. Document (`doc.*`)

Mutates fields on the document that triggered the rule.

- **Root Fields**: `doc.status`, `doc.naming_series`.
- **Note**: In V1, deep document path assignments for child tables (e.g., `doc.items.0.qty`) are not supported directly via this action.

### 2. Context Variables (`vars.*`)

Mutates variables in the execution context.

- **Nesting**: Supports deep paths like `vars.totals.tax_amount`.
- **Auto-Initialization**: Intermediate dictionaries are created automatically if they don't exist.

## Configuration (JSON)

The configuration is stored as a JSON array of assignment objects:

```json
[
	{
		"target": "doc.status",
		"operator": "set",
		"value": "Closed"
	},
	{
		"target": "vars.counter",
		"operator": "increment",
		"value": 1
	}
]
```

## Safety & Restrictions

- **System Protection**: Mutations to paths starting with `meta.`, `frappe.`, `rule.`, or `caller.` are blocked.
- **Event Awareness**: `doc.*` mutations are prohibited during `after_save` and other read-only events to prevent inconsistent states.
- **Sandboxed Evaluation**: Values are evaluated using Jinja templates with a restricted `SafeFrappeAPI` context.
